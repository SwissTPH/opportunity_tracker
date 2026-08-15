import json

from tracker.models import BudgetTemplate, BudgetTemplateColumn, BudgetTemplateRow, Currency, OpportunityBudget, OpportunityBudgetValue


def create_budget(opportunity, budget_payload):

    payload = json.loads(budget_payload)

    template = BudgetTemplate.objects.get(is_active=True)

    budget = OpportunityBudget.objects.create(
        opportunity=opportunity, template=template, ex_rate_to_default_cur=payload.get("exchange_rate"), ex_currency=Currency.objects.get(code=payload.get("ex_currency")))

    values_to_create = []

    for item in payload.get("values", []):
        row = BudgetTemplateRow.objects.get(
            template=template, key=item["row"])

        column = BudgetTemplateColumn.objects.get(
            template=template, key=item["column"])

        values_to_create.append(
            OpportunityBudgetValue(
                budget=budget,
                row=row,
                column=column,
                value=item["value"]
            )
        )

    OpportunityBudgetValue.objects.bulk_create(values_to_create)
