"""/land-and-deploy skill (SKILL-15, Plan 05-06).

4-phase pipeline: precondition → CI wait → deploy → health probe →
write deploy.md. See handler.py for the full implementation.
"""
from clawteam.templates.gstack.skills.land_and_deploy.handler import (
    land_and_deploy_handler,
)

__all__ = ["land_and_deploy_handler"]
