from __future__ import annotations
from typing import Any, Dict, List, Mapping, NotRequired, TypedDict


class StatusSepc(TypedDict, total=False):
    id: int
    label: str
    group: NotRequired[str]
    terminal: NotRequired[bool]


class WorkflowDefinition(TypedDict):
    version: str
    description: str
    statuses: Dict[str, StatusSepc]
    transitions: Dict[str, List[str]]
    required_fields: Dict[str, List[str]]

# Validations


def validate_workflow(workflow: Mapping[str, Any]) -> None:
    """
    Validate workflow structure and semantics.
    Raise ValueError with actionable message on first failure.
    """
    _validate_top_level_keys(workflow)
    _validate_top_level_types(workflow)

    statuses = workflow["statuses"]
    transitions = workflow["transitions"]
    required_fields = workflow["required_fields"]


def _validate_top_level_keys(workflow: Mapping[str, Any]) -> None:
    required = {"version", "description",
                "statuses", "transitions", "required_fields"}
    missing = required - set(workflow.keys())
    if missing:
        raise ValueError(f"Workflow missing required keys: {sorted(missing)}")


def _validate_top_level_types(workflow: Mapping[str, Any]) -> None:
    if not isinstance(workflow["version"], str) or not workflow["version"].strip():
        raise ValueError("Version must be non-empty string")

    if not isinstance(workflow["description"], str) or not workflow["description"].strip():
        raise ValueError("description must be a non-empty string")

    if not isinstance(workflow["statuses"], dict) or not workflow["statuses"]:
        raise ValueError("statuses must be a non-empty dict")

    if not isinstance(workflow["transitions"], dict):
        raise ValueError("transitions must be a dict")

    if not isinstance(workflow["required_fields"], dict):
        raise ValueError("required_fields must be a dict")


def _validate_statuses(statuses: Mapping[str, Any]) -> None:
    seen_ids = set()

    for slug, spec in statuses.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError("Each status key must be a non-empty slug string")

        if not isinstance(spec, dict):
            raise ValueError(f"Status '{slug}' must be a dict")

        if "id" not in spec or "label" not in spec:
            raise ValueError(f"Status '{slug}' must define id and label")

        status_id = spec["id"]
        label = spec["label"]

        if not isinstance(status_id, int):
            raise ValueError(f"Status '{slug}' id must be int")

        if status_id in seen_ids:
            raise ValueError(f"Duplicate status id found: {status_id}")
        seen_ids.add(status_id)

        if not isinstance(label, str) or not label.strip():
            raise ValueError(
                f"Status '{slug}' label must be a non-empty string")

        if "group" in spec and not isinstance(spec["group"], str):
            raise ValueError(
                f"Status '{slug}' group must be a string if provided")

        if "terminal" in spec and not isinstance(spec["terminal"], bool):
            raise ValueError(
                f"Status '{slug}' terminal must be bool if provided")


def _validate_transitions(
    statuses: Mapping[str, Any], transitions: Mapping[str, Any]
) -> None:
    status_slugs = set(statuses.keys())

    for from_slug, to_slugs in transitions.items():
        if from_slug not in status_slugs:
            raise ValueError(
                f"Transition source '{from_slug}' is not a defined status")

        if not isinstance(to_slugs, list):
            raise ValueError(f"Transitions for '{from_slug}' must be a list")

        seen_targets = set()
        for to_slug in to_slugs:
            if not isinstance(to_slug, str):
                raise ValueError(
                    f"Transition target in '{from_slug}' must be a string slug")

            if to_slug not in status_slugs:
                raise ValueError(
                    f"Transition target '{to_slug}' from '{from_slug}' is undefined"
                )

            if to_slug in seen_targets:
                raise ValueError(
                    f"Duplicate transition '{from_slug} -> {to_slug}' is not allowed"
                )
            seen_targets.add(to_slug)

            # Optional guardrail: avoid no-op transitions like submitted -> submitted.
            if to_slug == from_slug:
                raise ValueError(
                    f"Self transition '{from_slug} -> {to_slug}' is not allowed")


def _validate_required_fields(
    statuses: Mapping[str, Any], required_fields: Mapping[str, Any]
) -> None:
    status_slugs = set(statuses.keys())

    for target_slug, fields in required_fields.items():
        if target_slug not in status_slugs:
            raise ValueError(
                f"required_fields contains unknown status '{target_slug}'"
            )

        if not isinstance(fields, list):
            raise ValueError(
                f"required_fields['{target_slug}'] must be a list")

        seen_fields = set()
        for field_name in fields:
            if not isinstance(field_name, str) or not field_name.strip():
                raise ValueError(
                    f"required_fields['{target_slug}'] must contain non-empty field names"
                )
            if field_name in seen_fields:
                raise ValueError(
                    f"Duplicate field '{field_name}' in required_fields['{target_slug}']"
                )
            seen_fields.add(field_name)

# Helper function for the rest of the app


def get_status_slug_to_id(workflow: Mapping[str, Any]) -> Dict[str, int]:
    """
    Returns: {'entered': 1, 'go': 2, ...}
    """
    return {slug: int(spec["id"]) for slug, spec in workflow["statuses"].items()}


def get_status_id_to_slug(workflow: Mapping[str, Any]) -> Dict[int, str]:
    """
    Returns: {1: 'entered', 2: 'go', ...}
    """
    return {int(spec["id"]): slug for slug, spec in workflow["statuses"].items()}


def get_status_choices(workflow: Mapping[str, Any]) -> List[tuple[int, str]]:
    """
    Django choices format, sorted by numeric id:
    [(1, 'Entered'), (2, 'Go'), ...]
    """
    pairs = [
        (int(spec["id"]), str(spec["label"]))
        for spec in workflow["statuses"].values()
    ]
    pairs.sort(key=lambda item: item[0])
    return pairs


def get_allowed_next_slugs(workflow: Mapping[str, Any], current_slug: str) -> List[str]:
    """
    Safe transition lookup.
    """
    return list(workflow["transitions"].get(current_slug, []))
