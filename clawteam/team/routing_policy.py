"""Routing policy and state for tmux runtime message injection."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from clawteam.team.models import get_data_dir

_RECENT_EVENT_LIMIT = 50
_PENDING_SUMMARY_LIMIT = 5
_CYCLE_WINDOW = 20  # D-20: last 20 recentEvents form the cycle-detection window
_CYCLE_THRESHOLD = 3  # D-20: >=3 A->B AND >=3 B->A with matching topic hash
_PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_datetime(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    return _utcnow()


def _isoformat(value: datetime | str | None) -> str:
    return _ensure_datetime(value).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def _runtime_state_path(team_name: str) -> Path:
    return get_data_dir() / "teams" / team_name / "runtime_state.json"


@dataclass
class RuntimeEnvelope:
    source: str
    target: str
    channel: str = "direct"
    priority: str = "medium"
    message_type: str = "message"
    summary: str = ""
    evidence: list[str] = field(default_factory=list)
    recommended_next_action: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    requires_injection: bool = True
    requires_blackboard_update: bool = False
    dedupe_key: str = ""
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeEnvelope":
        return cls(**data)


@dataclass
class RouteDecision:
    action: str
    reason: str
    envelope: RuntimeEnvelope
    route_key: str
    flush_after: str | None = None
    aggregated_count: int = 0
    is_flush: bool = False


class RoutingPolicy(ABC):
    """Policy interface for runtime routing decisions."""

    @abstractmethod
    def decide(self, envelope: RuntimeEnvelope, now: datetime | str | None = None) -> RouteDecision:
        """Decide how to handle a normalized runtime envelope."""


class DefaultRoutingPolicy(RoutingPolicy):
    """Phase 1 tmux-only routing policy with simple same-pair throttling."""

    def __init__(self, team_name: str, throttle_seconds: int = 30):
        self.team_name = team_name
        self.throttle_seconds = throttle_seconds

    def decide(self, envelope: RuntimeEnvelope, now: datetime | str | None = None) -> RouteDecision:
        now_dt = _ensure_datetime(now)
        state = self.read_state()
        route_key = self._route_key(envelope.source, envelope.target)

        # ── Phase 2: cycle detection BEFORE existing throttle (§02-CONTEXT D-18) ──
        # Reuses the existing `recentEvents` 50-entry bounded window (specifics lesson #1).
        topic_hash = self._topic_hash(envelope)

        # Honor existing suppression first — if this topic is already suppressed on this
        # route, short-circuit WITHOUT re-emitting CycleDetected (dedupe: D-21).
        existing_route = state["routes"].get(route_key) or {}
        suppressed_existing = set(existing_route.get("suppressedTopics", []))
        if topic_hash in suppressed_existing:
            # Write a recentEvents entry tagged with topicHash so downstream
            # observers can see the suppression was honored.
            route = state["routes"].setdefault(route_key, self._empty_route(envelope))
            self._refresh_route(route, envelope)
            route["lastDispatchStatus"] = "suppressed"
            route["lastDispatchAt"] = now_dt.isoformat()
            route["lastDecisionReason"] = "cycle_suppressed_existing"
            self._append_event(
                state,
                route_key,
                route,
                action="cycle_suppressed",
                reason="cycle_suppressed_existing",
                summary=envelope.summary,
                timestamp=now_dt,
                topic_hash=topic_hash,
            )
            self._save_state(state)
            return RouteDecision(
                action="suppress",
                reason="cycle_suppressed_existing",
                envelope=envelope,
                route_key=route_key,
            )

        cycle_hit = self._detect_cycle(state, envelope, topic_hash)
        if cycle_hit is not None:
            route = state["routes"].setdefault(route_key, self._empty_route(envelope))
            self._refresh_route(route, envelope)
            suppressed_list = route.setdefault("suppressedTopics", [])
            if topic_hash not in suppressed_list:
                suppressed_list.append(topic_hash)
            route["lastDispatchStatus"] = "suppressed"
            route["lastDispatchAt"] = now_dt.isoformat()
            route["lastDecisionReason"] = "cycle_detected"
            self._append_event(
                state,
                route_key,
                route,
                action="cycle_suppressed",
                reason="cycle_detected",
                summary=envelope.summary,
                timestamp=now_dt,
                topic_hash=topic_hash,
            )
            # Persist state BEFORE emitting so handlers observe the on-disk suppression
            # (Pitfall #7 — sync emit after state save).
            self._save_state(state)
            try:
                from clawteam.events.global_bus import get_event_bus
                from clawteam.events.types import CycleDetected

                get_event_bus().emit(
                    CycleDetected(
                        team_name=self.team_name,
                        pair=(envelope.source, envelope.target),
                        topic_hash=topic_hash,
                        route_keys=cycle_hit["route_keys"],
                        window_size=_CYCLE_WINDOW,
                    )
                )
            except Exception:
                pass
            return RouteDecision(
                action="suppress",
                reason="cycle_detected",
                envelope=envelope,
                route_key=route_key,
            )

        # ── Existing throttle / inject flow (unchanged below this point) ──
        route = state["routes"].setdefault(route_key, self._empty_route(envelope))
        self._refresh_route(route, envelope)

        last_injected_at = _parse_iso(route.get("lastInjectedAt"))
        throttle_deadline = None
        if last_injected_at is not None:
            throttle_deadline = last_injected_at + timedelta(seconds=self.throttle_seconds)

        if throttle_deadline is not None and now_dt < throttle_deadline:
            self._append_pending(route, envelope, now_dt, throttle_deadline)
            route["lastDispatchStatus"] = "aggregated"
            route["lastDispatchAt"] = now_dt.isoformat()
            route["lastDecisionReason"] = "throttled"
            route["lastError"] = ""
            self._append_event(
                state,
                route_key,
                route,
                action="aggregated",
                reason="throttled",
                summary=envelope.summary,
                timestamp=now_dt,
                topic_hash=topic_hash,
            )
            self._save_state(state)
            return RouteDecision(
                action="aggregate",
                reason="throttled",
                envelope=envelope,
                route_key=route_key,
                flush_after=route["flushAfter"],
                aggregated_count=route["pendingCount"],
            )

        route["lastDispatchStatus"] = "pending"
        route["lastDispatchAt"] = now_dt.isoformat()
        route["lastDecisionReason"] = "inject_now"
        route["lastError"] = ""
        self._append_event(
            state,
            route_key,
            route,
            action="pending",
            reason="inject_now",
            summary=envelope.summary,
            timestamp=now_dt,
            topic_hash=topic_hash,
        )
        self._save_state(state)
        return RouteDecision(
            action="inject",
            reason="inject_now",
            envelope=envelope,
            route_key=route_key,
        )

    def flush_due(
        self,
        *,
        target_agent: str | None = None,
        now: datetime | str | None = None,
    ) -> list[RouteDecision]:
        now_dt = _ensure_datetime(now)
        state = self.read_state()
        decisions: list[RouteDecision] = []

        for route_key, route in state["routes"].items():
            flush_after = _parse_iso(route.get("flushAfter"))
            if route.get("pendingCount", 0) <= 0 or flush_after is None or flush_after > now_dt:
                continue
            if target_agent and route.get("target") != target_agent:
                continue

            envelope = self._build_aggregate_envelope(route, now_dt)
            route["lastDispatchStatus"] = "pending_flush"
            route["lastDispatchAt"] = now_dt.isoformat()
            route["lastDecisionReason"] = "flush_due"
            route["lastError"] = ""
            self._append_event(
                state,
                route_key,
                route,
                action="pending_flush",
                reason="flush_due",
                summary=envelope.summary,
                timestamp=now_dt,
            )
            decisions.append(
                RouteDecision(
                    action="inject",
                    reason="flush_due",
                    envelope=envelope,
                    route_key=route_key,
                    flush_after=route.get("flushAfter"),
                    aggregated_count=route.get("pendingCount", 0),
                    is_flush=True,
                )
            )

        if decisions:
            self._save_state(state)
        return decisions

    def record_dispatch_result(
        self,
        decision: RouteDecision,
        *,
        success: bool,
        now: datetime | str | None = None,
        error: str = "",
    ) -> None:
        now_dt = _ensure_datetime(now)
        state = self.read_state()
        route = state["routes"].setdefault(
            decision.route_key,
            self._empty_route(decision.envelope),
        )
        self._refresh_route(route, decision.envelope)
        route["lastDispatchAt"] = now_dt.isoformat()
        route["lastDecisionReason"] = decision.reason

        if success:
            route["lastDispatchStatus"] = "flushed" if decision.is_flush else "injected"
            route["lastInjectedAt"] = now_dt.isoformat()
            route["lastError"] = ""
            if decision.is_flush:
                self._clear_pending(route)
            self._append_event(
                state,
                decision.route_key,
                route,
                action=route["lastDispatchStatus"],
                reason=decision.reason,
                summary=decision.envelope.summary,
                timestamp=now_dt,
            )
        else:
            route["lastDispatchStatus"] = "failed"
            route["lastError"] = error or "runtime injection failed"
            if not decision.is_flush:
                self._append_pending(route, decision.envelope, now_dt, self._retry_after(now_dt))
            elif route.get("pendingCount", 0) > 0:
                self._schedule_retry(route, now_dt)
            self._append_event(
                state,
                decision.route_key,
                route,
                action="failed",
                reason=decision.reason,
                summary=decision.envelope.summary,
                timestamp=now_dt,
                error=route["lastError"],
            )

        self._save_state(state)

    def read_state(self) -> dict[str, Any]:
        path = _runtime_state_path(self.team_name)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}
        data.setdefault("team", self.team_name)
        data.setdefault("throttleSeconds", self.throttle_seconds)
        data.setdefault("updatedAt", "")
        data.setdefault("routes", {})
        data.setdefault("recentEvents", [])
        return data

    def _save_state(self, state: dict[str, Any]) -> None:
        path = _runtime_state_path(self.team_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        state["team"] = self.team_name
        state["throttleSeconds"] = self.throttle_seconds
        state["updatedAt"] = _utcnow().isoformat()

        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False)
            Path(tmp_name).replace(path)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _route_key(source: str, target: str) -> str:
        return f"{source}->{target}"

    def _empty_route(self, envelope: RuntimeEnvelope) -> dict[str, Any]:
        return {
            "source": envelope.source,
            "target": envelope.target,
            "channel": envelope.channel,
            "priority": envelope.priority,
            "lastDispatchStatus": "idle",
            "lastDispatchAt": "",
            "lastDecisionReason": "",
            "lastInjectedAt": "",
            "lastError": "",
            "pendingCount": 0,
            "pendingSummaries": [],
            "pendingEnvelopes": [],
            "pendingFirstBufferedAt": "",
            "pendingLastBufferedAt": "",
            "flushAfter": "",
        }

    def _refresh_route(self, route: dict[str, Any], envelope: RuntimeEnvelope) -> None:
        route["source"] = envelope.source
        route["target"] = envelope.target
        route["channel"] = envelope.channel
        route["priority"] = self._max_priority(route.get("priority", "medium"), envelope.priority)

    def _append_pending(
        self,
        route: dict[str, Any],
        envelope: RuntimeEnvelope,
        now_dt: datetime,
        flush_after: datetime,
    ) -> None:
        pending = list(route.get("pendingEnvelopes", []))
        pending.append(envelope.to_dict())
        route["pendingEnvelopes"] = pending
        route["pendingCount"] = len(pending)
        route["pendingSummaries"] = [
            item.get("summary", "")
            for item in pending[-_PENDING_SUMMARY_LIMIT:]
            if item.get("summary")
        ]
        if not route.get("pendingFirstBufferedAt"):
            route["pendingFirstBufferedAt"] = now_dt.isoformat()
        route["pendingLastBufferedAt"] = now_dt.isoformat()
        route["flushAfter"] = flush_after.isoformat()

    def _schedule_retry(self, route: dict[str, Any], now_dt: datetime) -> None:
        route["flushAfter"] = self._retry_after(now_dt).isoformat()

    def _retry_after(self, now_dt: datetime) -> datetime:
        return now_dt + timedelta(seconds=self.throttle_seconds)

    @staticmethod
    def _clear_pending(route: dict[str, Any]) -> None:
        route["pendingCount"] = 0
        route["pendingSummaries"] = []
        route["pendingEnvelopes"] = []
        route["pendingFirstBufferedAt"] = ""
        route["pendingLastBufferedAt"] = ""
        route["flushAfter"] = ""

    def _build_aggregate_envelope(self, route: dict[str, Any], now_dt: datetime) -> RuntimeEnvelope:
        pending = [RuntimeEnvelope.from_dict(item) for item in route.get("pendingEnvelopes", [])]
        count = len(pending)
        evidence = [f"- {item.summary}" for item in pending[:_PENDING_SUMMARY_LIMIT] if item.summary]
        if count > _PENDING_SUMMARY_LIMIT:
            evidence.append(f"- ... {count - _PENDING_SUMMARY_LIMIT} more update(s)")
        latest_action = next(
            (item.recommended_next_action for item in reversed(pending) if item.recommended_next_action),
            None,
        )
        return RuntimeEnvelope(
            source=route.get("source", ""),
            target=route.get("target", ""),
            channel=route.get("channel", "direct"),
            priority=route.get("priority", "medium"),
            message_type="aggregate",
            summary=(
                f"{count} queued runtime update"
                f"{'s' if count != 1 else ''} from {route.get('source', 'system')}."
            ),
            evidence=evidence,
            recommended_next_action=latest_action,
            payload={"aggregatedCount": count},
            dedupe_key=f"{route.get('source', '')}:{route.get('target', '')}:aggregate:{now_dt.isoformat()}",
            created_at=now_dt.isoformat(),
        )

    def _append_event(
        self,
        state: dict[str, Any],
        route_key: str,
        route: dict[str, Any],
        *,
        action: str,
        reason: str,
        summary: str,
        timestamp: datetime,
        error: str = "",
        topic_hash: str = "",
        progress_signal: bool = False,
    ) -> None:
        event: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "routeKey": route_key,
            "source": route.get("source", ""),
            "target": route.get("target", ""),
            "action": action,
            "reason": reason,
            "summary": summary,
            "pendingCount": route.get("pendingCount", 0),
        }
        if error:
            event["error"] = error
        # D-19/D-20: topicHash lets _detect_cycle match round-trips in the tail-20 window.
        # Always written (empty string allowed) so downstream consumers can rely on the key.
        event["topicHash"] = topic_hash
        # Plan 02-09 theater-detector populates `progressSignal` on entries where the
        # agent shipped artifact bytes or TaskCompleted fired during the turn; cycle
        # detector reads this flag to skip the streak on legitimate iteration
        # (Pitfall #3). Written unconditionally (default False) so readers of
        # `recentEvents` can rely on the key being present.
        event["progressSignal"] = bool(progress_signal)
        state["recentEvents"] = (state.get("recentEvents", []) + [event])[-_RECENT_EVENT_LIMIT:]

    # ── Phase 2: cycle detector helpers (§02-CONTEXT D-18..D-21) ─────────────────

    def _topic_hash(self, envelope: RuntimeEnvelope) -> str:
        """Priority chain for the cycle-detection topic hash (D-19).

        1. envelope.dedupe_key (strongest signal — deliberately set by router)
        2. envelope.payload['request_id'] or 'requestId' (TeamMessage round-trip)
        3. sha1(content[:128])[:16] (content-similarity fallback)
        """
        if envelope.dedupe_key:
            return envelope.dedupe_key
        payload = getattr(envelope, "payload", None) or {}
        req_id: Any = None
        if isinstance(payload, dict):
            req_id = payload.get("request_id") or payload.get("requestId")
        if req_id:
            return str(req_id)
        content = ""
        if isinstance(payload, dict):
            content = payload.get("content") or ""
        content = content or (envelope.summary or "")
        return hashlib.sha1(content[:128].encode("utf-8")).hexdigest()[:16]

    def _detect_cycle(
        self,
        state: dict[str, Any],
        envelope: RuntimeEnvelope,
        topic_hash: str,
    ) -> dict[str, Any] | None:
        """Return cycle-hit dict when >=3 round-trips share topic_hash in the last-20 window.

        Pitfall #3 mitigation: if any entry in the window carries
        ``progressSignal: True`` (populated by Plan 02-09 theater detector on
        TaskCompleted), the streak is broken and we return None so legitimate
        iteration does not false-positive.
        """
        window = state.get("recentEvents", [])[-_CYCLE_WINDOW:]
        route_a_b = self._route_key(envelope.source, envelope.target)
        route_b_a = self._route_key(envelope.target, envelope.source)
        count_ab = 0
        count_ba = 0
        progress_signal = False
        for entry in window:
            entry_topic = entry.get("topicHash", "")
            if entry_topic != topic_hash:
                continue
            if entry.get("progressSignal"):
                progress_signal = True
            if entry.get("routeKey") == route_a_b:
                count_ab += 1
            elif entry.get("routeKey") == route_b_a:
                count_ba += 1
        if progress_signal:
            return None  # Pitfall #3: legitimate iteration — skip cycle trip.
        if count_ab >= _CYCLE_THRESHOLD and count_ba >= _CYCLE_THRESHOLD:
            return {
                "topic_hash": topic_hash,
                "route_keys": [route_a_b, route_b_a],
                "reason": (
                    f"{_CYCLE_THRESHOLD}+ round-trips in {_CYCLE_WINDOW}-msg window "
                    f"(A->B={count_ab}, B->A={count_ba})"
                ),
            }
        return None

    @staticmethod
    def _max_priority(left: str, right: str) -> str:
        return left if _PRIORITY_ORDER.get(left, 1) >= _PRIORITY_ORDER.get(right, 1) else right
