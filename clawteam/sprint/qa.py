"""Question / Answer pydantic models + D-08 markdown-frontmatter serialization.

Per RFC 001 §4.5 (the interaction gate's file-layout anchor) and context D-07
(8-char hex ID format) and D-08 (the markdown-frontmatter schema). Parsing
uses a stdlib-only minimal frontmatter reader — PROJECT.md constraint
"no new required runtime deps for core harness extensions" rules out pyyaml.

The schema is intentionally narrow:
- Flat `key: value` lines (scalar string values; inline `# comment` stripped).
- One nested list: `choices:` with `{id, label}` entries (exactly two keys).
- Body prose is preserved verbatim below the closing `---` fence.

When Phase 4 needs richer structure (nested dicts, multi-line values, anchors),
the parser is swapped for a real YAML parser behind the same public API.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

QuestionType = Literal["multi-choice", "freeform", "confirm"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Choice(BaseModel):
    """One option in a multi-choice question. Two keys: id + label."""

    id: str
    label: str


class Question(BaseModel):
    """D-08 question schema. Written to `<sprint_dir>/questions/<id>.md`."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    slug: str
    type: QuestionType
    created_at: str = Field(default_factory=_now_iso)
    sprint_id: str
    phase: str
    author: str
    choices: list[Choice] | None = None
    body: str = ""

    @model_validator(mode="after")
    def _validate_choices_match_type(self) -> Question:
        if self.type == "multi-choice":
            if not self.choices:
                raise ValueError("multi-choice questions require at least one choice")
        else:
            if self.choices:
                raise ValueError("freeform/confirm questions must not declare choices")
        return self

    # ── Markdown ─────────────────────────────────────────────────────

    def to_markdown(self) -> str:
        """Emit the D-08 markdown form: frontmatter + blank line + body."""
        lines = ["---"]
        lines.append(f"id: {self.id}")
        lines.append(f"slug: {self.slug}")
        lines.append(f"type: {self.type}")
        lines.append(f"created_at: {self.created_at}")
        lines.append(f"sprint_id: {self.sprint_id}")
        lines.append(f"phase: {self.phase}")
        lines.append(f"author: {self.author}")
        if self.type == "multi-choice" and self.choices:
            lines.append("choices:")
            for choice in self.choices:
                lines.append(f"  - id: {choice.id}")
                lines.append(f"    label: {choice.label}")
        lines.append("---")
        body = self.body or ""
        if body and not body.startswith("\n"):
            body = "\n" + body
        if body and not body.endswith("\n"):
            body = body + "\n"
        return "\n".join(lines) + body + ("\n" if not body else "")

    @classmethod
    def from_markdown(cls, raw: str) -> Question:
        """Parse the D-08 markdown form back into a Question."""
        meta, body = _parse_frontmatter(raw)
        choices_raw = meta.pop("choices", None)
        if choices_raw is not None:
            meta["choices"] = [Choice(**entry) for entry in choices_raw]
        meta["body"] = body
        return cls(**meta)


class Answer(BaseModel):
    """D-08 answer schema. Written to `<sprint_dir>/answers/<question.id>.md`."""

    question_id: str
    answered_at: str = Field(default_factory=_now_iso)
    choice: str | None = None
    body: str = ""

    # ── Markdown ─────────────────────────────────────────────────────

    def to_markdown(self) -> str:
        lines = ["---"]
        lines.append(f"question_id: {self.question_id}")
        lines.append(f"answered_at: {self.answered_at}")
        if self.choice is not None:
            lines.append(f"choice: {self.choice}")
        lines.append("---")
        body = self.body or ""
        if body and not body.startswith("\n"):
            body = "\n" + body
        if body and not body.endswith("\n"):
            body = body + "\n"
        return "\n".join(lines) + body + ("\n" if not body else "")

    @classmethod
    def from_markdown(cls, raw: str) -> Answer:
        meta, body = _parse_frontmatter(raw)
        meta["body"] = body
        return cls(**meta)


# ── Stdlib-only frontmatter parser ───────────────────────────────────

_INLINE_COMMENT = re.compile(r"\s+#.*$")


def _strip_inline_comment(value: str) -> str:
    """Strip ` # comment` / `\\t# comment` trailing text — not `value: foo#bar`."""
    return _INLINE_COMMENT.sub("", value).rstrip()


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Return (metadata_dict, body_string).

    Accepts exactly the D-08 shape. Raises ValueError on any other shape.
    """
    text = raw.lstrip("\ufeff")  # drop leading BOM if present
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise ValueError("invalid question/answer frontmatter: missing opening `---` fence")

    meta: dict = {}
    i = 1
    closing_index: int | None = None
    while i < len(lines):
        line = lines[i]
        if line.rstrip() == "---":
            closing_index = i
            break
        stripped = line.strip()
        if stripped == "":
            i += 1
            continue
        if line.startswith("  "):
            raise ValueError(
                f"invalid question/answer frontmatter: unexpected indented scalar at line {i + 1}"
            )
        # Flat key: value OR key: (list intro)
        if ":" not in line:
            raise ValueError(
                f"invalid question/answer frontmatter: non-key line at line {i + 1}: {line!r}"
            )
        key, _, value = line.partition(":")
        key = key.strip()
        value = _strip_inline_comment(value.strip())
        if value == "":
            # Must be followed by one or more "  - subkey: val" blocks (our only supported list shape).
            items: list[dict] = []
            i += 1
            while i < len(lines):
                sub = lines[i]
                if sub.strip() == "" and (i + 1 < len(lines)) and not lines[i + 1].startswith("  "):
                    # blank line ends the list
                    break
                if sub.rstrip() == "---":
                    break
                if not sub.startswith("  - "):
                    break
                entry: dict = {}
                # First sub-line: "  - sub_key: sub_val"
                sub_key_line = sub[len("  - "):]
                sk, sep, sv = sub_key_line.partition(":")
                if not sep:
                    raise ValueError(
                        f"invalid question/answer frontmatter: expected `key: value` after `- ` at line {i + 1}"
                    )
                entry[sk.strip()] = _strip_inline_comment(sv.strip())
                i += 1
                # Continuation sub-lines: "    sub_key: sub_val"
                while i < len(lines) and lines[i].startswith("    "):
                    cont = lines[i][4:]
                    ck, sep2, cv = cont.partition(":")
                    if not sep2:
                        raise ValueError(
                            f"invalid question/answer frontmatter: expected `key: value` in list entry at line {i + 1}"
                        )
                    entry[ck.strip()] = _strip_inline_comment(cv.strip())
                    i += 1
                items.append(entry)
            meta[key] = items
            continue
        else:
            meta[key] = value
            i += 1

    if closing_index is None:
        raise ValueError("invalid question/answer frontmatter: missing closing `---` fence")

    body_lines = lines[closing_index + 1:]
    # Strip at most one leading blank line to normalize the "\n---\n\nprose" shape.
    if body_lines and body_lines[0].strip() == "":
        body_lines = body_lines[1:]
    body = "\n".join(body_lines)
    if body and not body.endswith("\n"):
        body += "\n"
    return meta, body
