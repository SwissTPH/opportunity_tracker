from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from tracker.workflows.service import get_statuses_by_group
from tracker.workflows.registry import get_active_workflow
from tracker.workflows.schema import get_status_slug_to_id
from .pdf_processor import PDFProcessor
from tracker.models import FundingAgency, Opportunity
from .forms import FinancialFilterForm, OpportunityFilterForm
from .models import ReportConfig


def reports(request):
    return render(request, "reports/reports.html")


def get_report_config(slug) -> ReportConfig:
    try:
        report_config = ReportConfig.objects.get(slug=slug)
        field_config = report_config.config or {}
    except ReportConfig.DoesNotExist:
        field_config = {}

    return field_config


def get_opportunities(request):
    # Load the report config for 'opportunity' to determine field visibility
    field_config = get_report_config('opportunity')

    form = OpportunityFilterForm(request.GET or None)

    # Hide fields that are not visible in the config (where value is False)
    from django import forms
    for field_name, is_visible in field_config.items():
        if not is_visible and field_name in form.fields:
            # Use HiddenInput to hide the field instead of deleting it
            form.fields[field_name].widget = forms.HiddenInput()
            form.fields[field_name].required = False

    context = {'form': form, 'field_config': field_config}
    subtitle = []

    if request.GET.get("preview") and form.is_valid():
        opp_type = form.cleaned_data.get("opp_type", None)
        status = form.cleaned_data.get("status", None)
        currency = form.cleaned_data.get("currency", None)
        client = form.cleaned_data.get("client", None)
        funding_agency = form.cleaned_data.get("funding_agency", None)
        lead_unit = form.cleaned_data.get("lead_unit", None)
        lead_institute = form.cleaned_data.get("lead_institute", None)
        proposal_lead = form.cleaned_data.get("proposal_lead", None)
        created_by = form.cleaned_data.get("created_by", None)
        due_date_from = form.cleaned_data.get("due_date_from", None)
        due_date_to = form.cleaned_data.get("due_date_to", None)
        clarification_date_from = form.cleaned_data.get(
            "clarification_date_from", None)
        clarification_date_to = form.cleaned_data.get(
            "clarification_date_to", None)
        intent_bid_date_from = form.cleaned_data.get(
            "intent_bid_date_from", None)
        intent_bid_date_to = form.cleaned_data.get("intent_bid_date_to", None)
        submission_date_from = form.cleaned_data.get(
            "submission_date_from", None)
        submission_date_to = form.cleaned_data.get("submission_date_to", None)
        result_date_from = form.cleaned_data.get(
            "result_date_from", None)
        result_date_to = form.cleaned_data.get("result_date_to", None)
        created_from = form.cleaned_data.get("created_at_from", None)
        created_to = form.cleaned_data.get("created_at_to", None)
        is_noncompetitive = form.cleaned_data.get("is_noncompetitive", None)

        opportunities = Opportunity.objects.all().order_by("-created_at")

        if opp_type:
            opportunities = opportunities.filter(opp_type=opp_type)
            subtitle.append("Type: " + opp_type)
        if status:
            opportunities = opportunities.filter(status=status)
            # Get the human-readable status label
            status_display = dict(Opportunity.OPP_STATUS).get(
                int(status), status)
            subtitle.append("Status: " + str(status_display))
        if currency:
            opportunities = opportunities.filter(currency=currency)
            subtitle.append("Currency: " + str(currency))
        if client:
            opportunities = opportunities.filter(client=client)
            subtitle.append("Client: " + client.code)
        if funding_agency:
            opportunities = opportunities.filter(funding_agency=funding_agency)
            subtitle.append("Funding Agency: " + funding_agency.code)
        if lead_unit:
            opportunities = opportunities.filter(lead_unit=lead_unit)
            subtitle.append("Lead Unit: " + lead_unit.code)
        if lead_institute:
            opportunities = opportunities.filter(lead_institute=lead_institute)
            subtitle.append("Lead Institute: " + lead_institute.code)
        if proposal_lead:
            opportunities = opportunities.filter(proposal_lead=proposal_lead)
            subtitle.append(
                "Proposal Lead: " + proposal_lead.first_name + ' ' + proposal_lead.last_name)
        if created_by:
            opportunities = opportunities.filter(created_by=created_by)
            subtitle.append(
                "Created by: " + created_by.first_name + ' ' + created_by.last_name)
        if due_date_from:
            opportunities = opportunities.filter(due_date__gte=due_date_from)
            subtitle.append("Due date from: " +
                            due_date_from.strftime("%d.%m.%Y"))
        if due_date_to:
            opportunities = opportunities.filter(due_date__lte=due_date_to)
            subtitle.append("Due date to: " +
                            due_date_to.strftime("%d.%m.%Y"))
        if clarification_date_from:
            opportunities = opportunities.filter(
                clarification_date__gte=clarification_date_from)
            subtitle.append("Clarification date from: " +
                            clarification_date_from.strftime("%d.%m.%Y"))
        if clarification_date_to:
            opportunities = opportunities.filter(
                clarification_date__lte=clarification_date_to)
            subtitle.append("Clarification date to: " +
                            clarification_date_to.strftime("%d.%m.%Y"))
        if intent_bid_date_from:
            opportunities = opportunities.filter(
                intent_bid_date__gte=intent_bid_date_from)
            subtitle.append("Intent to bid from: " +
                            intent_bid_date_from.strftime("%d.%m.%Y"))
        if intent_bid_date_to:
            opportunities = opportunities.filter(
                intent_bid_date__lte=intent_bid_date_to)
            subtitle.append("Intent to bid to: " +
                            intent_bid_date_to.strftime("%d.%m.%Y"))
        if submission_date_from:
            opportunities = opportunities.filter(
                submission_date__gte=submission_date_from)
            subtitle.append("Submission date from: " +
                            submission_date_from.strftime("%d.%m.%Y"))
        if submission_date_to:
            opportunities = opportunities.filter(
                submission_date__lte=submission_date_to)
            subtitle.append("Submission date to: " +
                            submission_date_to.strftime("%d.%m.%Y"))
        if result_date_from:
            opportunities = opportunities.filter(
                result_date__gte=result_date_from)
            subtitle.append("Result date from: " +
                            result_date_from.strftime("%d.%m.%Y"))
        if result_date_to:
            opportunities = opportunities.filter(
                result_date__lte=result_date_to)
            subtitle.append("Result date to: " +
                            result_date_to.strftime("%d.%m.%Y"))
        if created_from:
            opportunities = opportunities.filter(created_at__gte=created_from)
            subtitle.append("Created date from: " +
                            created_from.strftime("%d.%m.%Y"))
        if created_to:
            opportunities = opportunities.filter(created_at__lte=created_to)
            subtitle.append("Created date to: " +
                            created_to.strftime("%d.%m.%Y"))
        if is_noncompetitive:
            opportunities = opportunities.filter(
                is_noncompetitive=is_noncompetitive)
            subtitle.append(
                "Competition Type: " + ("Non-Competitive" if is_noncompetitive == "True" else "Competitive"))

        template = "reports/report_templates/opportunities.html"
        response = PDFProcessor.process(
            request, template, opportunities, subtitle=" | ".join(subtitle),  footnote="Opportunities in green are non competitive", filename="Opportunities.pdf")
        return response

    return render(request, "reports/opportunities.html", context)


def get_financial(request):
    # Load the report config for 'financial' to determine field visibility
    field_config = get_report_config('financial')

    form = FinancialFilterForm(request.GET or None)

    # Hide fields that are not visible in the config (where value is False)
    from django import forms
    for field_name, is_visible in field_config.items():
        if not is_visible and field_name in form.fields:
            # Use HiddenInput to hide the field instead of deleting it
            form.fields[field_name].widget = forms.HiddenInput()
            form.fields[field_name].required = False

    context = {'form': form, 'field_config': field_config}
    subtitle = []

    if form.is_valid():
        client = form.cleaned_data.get("client", None)
        funding_agency = form.cleaned_data.get("funding_agency", None)
        agency_type = form.cleaned_data.get("agency_type", None)
        report_date = form.cleaned_data.get(
            "report_date", timezone.localdate())

        current_year = report_date.year
        previous_year = current_year - 1
        two_years_ago = current_year - 2
        start_of_current_year = report_date.replace(month=1, day=1)

        subtitle.append("Reporting Date: " + report_date.strftime("%d.%m.%Y"))

        # Only consider the type RFP
        opportunities = Opportunity.objects.filter(opp_type="RFP")

        wf = get_active_workflow()
        slug_to_id = get_status_slug_to_id(wf)

        outcome_statuses = get_statuses_by_group(wf, "outcome")
        won_status_id = slug_to_id.get("won")
        submitted_status_ids = [
            status["id"]
            for status in outcome_statuses.values()
        ]
        submitted_status_id = slug_to_id.get("submitted")
        if submitted_status_id is not None:
            submitted_status_ids.append(submitted_status_id)

        opportunities = Opportunity.objects.filter(
            status__in=submitted_status_ids
        ).order_by("funding_agency__agency_type")

        if client:
            client = [value for value in client if value not in (None, "None")]
            opportunities = opportunities.filter(client__in=client)
            client_display = [c.code for c in client]
            subtitle.append("Client: " + ", ".join(client_display))
        if funding_agency:
            funding_agency = [
                value for value in funding_agency if value not in (None, "None")]
            opportunities = opportunities.filter(
                funding_agency__in=funding_agency)

            funding_agency_display = [agency.code for agency in funding_agency]
            subtitle.append("Funding Agency: " +
                            ", ".join(funding_agency_display))
        if agency_type:
            agency_type = [
                value for value in agency_type if value not in (None, "None")]
            if agency_type:
                opportunities = opportunities.filter(
                    funding_agency__agency_type__in=agency_type)
                agency_type_labels = dict(FundingAgency.AGENCY_TYPE)
                agency_type_display = [
                    agency_type_labels.get(value, value)
                    for value in agency_type
                ]
                subtitle.append("Agency Type: " +
                                ", ".join(agency_type_display))

        project_ratio = 12.0/report_date.month

        grouped_opportunities = (
            opportunities
            .values("funding_agency__agency_type")
            .annotate(
                won_previous_year=Count(
                    "id",
                    filter=Q(
                        status=won_status_id,
                        submission_date__year=two_years_ago,
                    ),
                ),
                won_last_year=Count(
                    "id",
                    filter=Q(
                        status=won_status_id,
                        submission_date__year=previous_year,
                    ),
                ),
                won_to_date=Count(
                    "id",
                    filter=Q(
                        status=won_status_id,
                        submission_date__gte=start_of_current_year,
                        submission_date__lte=report_date,
                    ),
                ),
                submitted_previous_year=Count(
                    "id",
                    filter=Q(
                        status__in=submitted_status_ids,
                        submission_date__year=two_years_ago,
                    ),
                ),
                submitted_last_year=Count(
                    "id",
                    filter=Q(
                        status__in=submitted_status_ids,
                        submission_date__year=previous_year,
                    ),
                ),
                submitted_to_date=Count(
                    "id",
                    filter=Q(
                        status__in=submitted_status_ids,
                        submission_date__gte=start_of_current_year,
                        submission_date__lte=report_date,
                    ),
                ),
            )
        )

        agency_type_labels = dict(FundingAgency.AGENCY_TYPE)
        rows = []
        for opportunity in grouped_opportunities:
            agency_type_value = opportunity["funding_agency__agency_type"]
            rows.append({
                "agency_type": agency_type_labels.get(
                    agency_type_value, "Unknown"),
                "won_previous_year": opportunity["won_previous_year"],
                "won_last_year": opportunity["won_last_year"],
                "won_projection": round(opportunity["won_to_date"] * project_ratio),
                "won_to_date": opportunity["won_to_date"],
                "submitted_previous_year": opportunity["submitted_previous_year"],
                "submitted_last_year": opportunity["submitted_last_year"],
                "submitted_projection": round(opportunity["submitted_to_date"] * project_ratio),
                "submitted_to_date": opportunity["submitted_to_date"],
            })

        total_fields = (
            "won_previous_year",
            "won_last_year",
            "won_projection",
            "won_to_date",
            "submitted_previous_year",
            "submitted_last_year",
            "submitted_projection",
            "submitted_to_date",
        )
        totals = {
            field: sum(row[field] for row in rows)
            for field in total_fields
        }
        rows.append({"agency_type": "All", **totals})

        context.update({
            "current_year": current_year,
            "previous_year": previous_year,
            "two_years_ago": two_years_ago,
            "report_date": report_date,
        })

        template = "reports/report_templates/financial.html"
        response = PDFProcessor.process(
            request,
            template,
            rows,
            subtitle=" | ".join(subtitle),
            filename="Financial.pdf",
            context=context
        )
        return response

    return render(request, "reports/financial.html", context)
