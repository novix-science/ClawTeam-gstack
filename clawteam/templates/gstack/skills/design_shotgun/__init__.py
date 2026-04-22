"""/design-shotgun skill — multi-turn variant generation state machine (SKILL-11, D-12).

Package layout:

* :mod:`~clawteam.templates.gstack.skills.design_shotgun.state` — pure state
  machine primitives (DSState/DSEvent enums, TRANSITIONS table, ShotgunState
  + VariantFixture dataclasses).
* :mod:`~clawteam.templates.gstack.skills.design_shotgun.handler` — multi-turn
  entry point that composes state transitions + side effects (variant file
  writes, memory-store taste observation, state.json persistence).
"""
from clawteam.templates.gstack.skills.design_shotgun.handler import shotgun_handler
from clawteam.templates.gstack.skills.design_shotgun.state import (
    DSEvent,
    DSState,
    ShotgunState,
    TRANSITIONS,
    VariantFixture,
)

__all__ = [
    "shotgun_handler",
    "DSEvent",
    "DSState",
    "ShotgunState",
    "TRANSITIONS",
    "VariantFixture",
]
