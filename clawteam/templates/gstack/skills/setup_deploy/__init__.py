"""/setup-deploy skill — one-time SRE-driven deploy-config wizard (SKILL-19).

Runs a questionary wizard (provider/project/custom_deploy_cmd), validates
adversarial input (shell metachars in slug + custom cmd — T-05-05-01/02 / D-15),
then atomically writes a ``[deploy]`` block into ``gstack.toml`` preserving
all other blocks (T-05-05-03). Idempotent on re-run (prompts overwrite).

Role-gated to ``sre`` only (T-05-05-04).
"""

from clawteam.templates.gstack.skills.setup_deploy.handler import (
    setup_deploy_handler,
)
from clawteam.templates.gstack.skills.setup_deploy.wizard import (
    run_wizard,
    validate_custom_cmd,
    validate_project_slug,
)

__all__ = [
    "setup_deploy_handler",
    "run_wizard",
    "validate_project_slug",
    "validate_custom_cmd",
]
