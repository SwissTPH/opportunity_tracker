from __future__ import annotations

from typing import Any, Dict, List, Tuple

from tracker.workflows.registry import get_active_workflow
from tracker.workflows.schema import get_status_id_to_slug


def get_current_status_slug(opportunity) -> str | None:
    """
    Return the workflow slug for the opportunity's current integer status.
    Returns None if the status is not recognised by the active workflow.
    """
    wf = get_active_workflow()
    return get_status_id_to_slug(wf).get(opportunity.status)


def get_allowed_next_statuses(opportunity) -> List[Tuple[int, str]]:
    """
    Return a list of (id, label) pairs representing the valid next statuses
    for this opportunity, filtered by any conditional transition rules
    (e.g. transfer_to_rfp only appears for EOI opportunities).

    This replaces the hardcoded if/elif block in OpportunityStatusUpdateView.
    """
    wf = get_active_workflow()
    current_slug = get_current_status_slug(opportunity)

    if not current_slug:
        return []

    candidate_slugs = wf["transitions"].get(current_slug, [])

    # Drop slugs not defined in the active workflow.
    candidate_slugs = [
        slug for slug in candidate_slugs if slug in wf["statuses"]]
    conditions = wf.get("transition_conditions", {})
    statuses = wf["statuses"]

    result = []
    for to_slug in candidate_slugs:
        edge_key = f"{current_slug}->{to_slug}"

        if edge_key in conditions:
            rule = conditions[edge_key]
            if rule["type"] == "field_equals":
                actual_value = getattr(opportunity, rule["field"], None)
                if str(actual_value).lower() != str(rule["value"]).lower():
                    # Condition not met — skip this transition
                    continue

        spec = statuses[to_slug]
        result.append((spec["id"], spec["label"]))

    return result


def get_required_fields(target_status_id: int) -> List[str]:
    """
    Return the list of field names that must be present when transitioning
    to the given target status id.

    This replaces hardcoded status-number checks in form clean() methods.
    """
    wf = get_active_workflow()
    target_slug = get_status_id_to_slug(wf).get(target_status_id)

    if not target_slug:
        return []

    return list(wf["required_fields"].get(target_slug, []))


def get_current_status_group(opportunity) -> str:
    """
    Return the group of the opportunity's current status (e.g. 'initial',
    'decision', 'execution', 'outcome', 'post_win').
    Returns empty string if not found.

    Used by templates to decide which action buttons to show without
    hardcoding status integer comparisons.
    """
    wf = get_active_workflow()
    current_slug = get_current_status_slug(opportunity)

    if not current_slug:
        return ""

    return wf["statuses"][current_slug].get("group", "")
