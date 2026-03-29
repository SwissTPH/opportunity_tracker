from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from django.conf import settings

from tracker.workflows.provider import load_workflow


@lru_cache(maxsize=1)
def get_active_workflow() -> Dict[str, Any]:
    """
    Return the active workflow definition configured in Django settings.

    Uses cache so workflow import/validation happens once per process.
    """
    dotted_path = getattr(settings, "WORKFLOW_DEFINITION", None)
    if not dotted_path:
        raise ValueError(
            "WORKFLOW_DEFINITION is not configured in Django settings."
        )

    return load_workflow(dotted_path)


def refresh_workflow_cache() -> None:
    """
    Clear cached workflow. Useful in tests when overriding settings.
    """
    get_active_workflow.cache_clear()
