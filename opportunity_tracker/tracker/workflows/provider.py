from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

from tracker.workflows.schema import validate_workflow


def load_workflow(dotted_path: str) -> Dict[str, Any]:
    """
    Import the workflow module at dotted_path, extract its WORKFLOW dict,
    validate it against the schema contract, and return it.

    Raises:
        ImportError  — if the module path cannot be resolved.
        AttributeError — if the module has no WORKFLOW variable.
        ValueError   — if the workflow fails schema validation.
    """
    try:
        module = import_module(dotted_path)
    except ImportError as e:
        raise ImportError(
            f"Could not import workflow module '{dotted_path}'. "
            f"Check WORKFLOW_DEFINITION in settings. Original error: {e}"
        ) from e

    workflow = getattr(module, "WORKFLOW", None)

    if workflow is None:
        raise AttributeError(
            f"Module '{dotted_path}' has no WORKFLOW variable. "
            f"Every workflow definition must expose a WORKFLOW dict."
        )

    # validate_workflow raises ValueError with a clear message if anything is wrong
    validate_workflow(workflow)

    return workflow
