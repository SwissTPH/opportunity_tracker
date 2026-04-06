"""
Test settings — inherits all production/dev config but forces the default
workflow so that every test runs against the full status set (including
transfer_to_rfp) regardless of what WORKFLOW_DEFINITION is set to in
.env files.
"""
from .settings import *  # noqa: F401, F403

WORKFLOW_DEFINITION = "tracker.workflows.definitions.default"
