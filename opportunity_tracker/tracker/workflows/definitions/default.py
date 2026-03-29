from tracker.workflows.schema import validate_workflow

WORKFLOW = {
    "version": "1.0.0",
    "description": "Default opportunity lifecycle",
    "statuses": {
        # Initial
        "entered": {"id": 1, "label": "Entered", "group": "initial"},

        # Decision
        "go": {"id": 2, "label": "Go", "group": "decision"},
        "no_go": {"id": 3, "label": "No-Go", "group": "decision", "terminal": True},
        "consider": {"id": 4, "label": "Consider", "group": "decision"},

        # Execution
        "submitted": {"id": 5, "label": "Submitted", "group": "execution"},

        # Outcome
        "lost": {"id": 6, "label": "Lost", "group": "outcome", "terminal": True},
        "won": {"id": 7, "label": "Won", "group": "outcome"},
        "cancelled": {"id": 8, "label": "Cancelled", "group": "outcome", "terminal": True},
        "assumed_lost": {"id": 9, "label": "Assumed Lost", "group": "outcome", "terminal": True},
        "na": {"id": 10, "label": "N/A", "group": "outcome", "terminal": True},
        "transfer_to_rfp": {"id": 11, "label": "Transfer to RFP", "group": "outcome", "terminal": True},

    },
    "transitions": {
        # Entered stage
        "entered": ["go", "no_go", "consider"],

        # Decision stage
        "consider": ["go", "no_go"],
        "go": ["submitted"],

        # Submitted stage
        "submitted": ["won", "lost", "cancelled", "assumed_lost", "na"],

        # Won stage and post-win
        "won": ["transfer_to_rfp"],

        # Terminal states intentionally have no outgoing transitions:
        # no_go, lost, cancelled, assumed_lost, na, transfer_to_rfp
    },
    "transition_conditions": {
        "won->transfer_to_rfp": {
            "type": "field_equals",
            "field": "opp_type",
            "value": "EOI",
        }
    },

    "required_fields": {
        # Fields required to move into a target status
        "go": ["proposal_lead", "lead_unit"],
        "submitted": ["submission_date", "lead_institute"],

        # Result statuses
        "won": ["result_date"],
        "lost": ["result_date"],
        "cancelled": ["result_date"],
        "assumed_lost": ["result_date"],
    }
}

# Fail fast on import if definition is malformed.
validate_workflow(WORKFLOW)
