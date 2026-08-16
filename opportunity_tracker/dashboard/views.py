from typing import Any

from django.db.models import Case, Count, IntegerField, Sum, When, Value
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.timezone import now
from django.views.generic import TemplateView

from tracker.models import Opportunity


class DashboardDataView(TemplateView):
    status_dict = dict(Opportunity.OPP_STATUS)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        year_period = request.GET.get("year", now().year)

        status_overview = self.get_status_overview(year_period)
        status_labels = status_overview["status_labels"]
        status_data = status_overview["status_data"]

        # Opportunities by Funding Agencies
        top_10_agencies = self.get_top_10_funding_agencies(year_period)
        funding_agency_labels = top_10_agencies["funding_agency_labels"]
        agency_dataset = top_10_agencies["agency_dataset"]

        # Opportunities by Lead Unit
        lead_units = self.get_opportunity_by_lead_unit(year_period)
        lead_unit_labels = lead_units["lead_unit_labels"]
        lead_unit_data = lead_units["lead_unit_data"]

        # Opportunities by Lead Institute
        lead_institutes = self.get_opportunity_by_lead_institute(year_period)
        lead_institute_labels = lead_institutes["lead_institute_labels"]
        lead_institute_data = lead_institutes["lead_institute_data"]

        # Opportunities by Proposal Lead
        proposal_lead = self.get_opportunity_by_proposal_lead(year_period)
        proposal_lead_labels = proposal_lead["proposal_lead_labels"]
        proposal_lead_data = proposal_lead["proposal_lead_data"]

        # Top 5 Valued Opportunities
        top5_valued_opportunities = self.get_top5_won_valued_opportunities(
            year_period)
        top5_won_valued_labels = top5_valued_opportunities["top5_won_valued_labels"]
        top5_won_valued_data = top5_valued_opportunities["top5_won_valued_data"]

        # Top 5 Valued Opportunities
        top5_valued_submitted = self.get_top5_valued_submitted(
            year_period)
        top5_valued_submitted_labels = top5_valued_submitted["top5_valued_submitted_labels"]
        top5_valued_submitted_data = top5_valued_submitted["top5_valued_submitted_data"]

        # Top 5 duration Opportunities
        top5_duration_opportunities_won = self.get_top5_duration_opportunities_won(
            year_period)
        top5_duration_won_labels = top5_duration_opportunities_won["top5_duration_won_labels"]
        top5_duration_won_data = top5_duration_opportunities_won["top5_duration_won_data"]

        # Top 5 duration Opportunities
        top5_duration_submitted = self.get_top5_duration_submitted(
            year_period)
        top5_duration_submitted_labels = top5_duration_submitted["top5_duration_submitted_labels"]
        top5_duration_submitted_data = top5_duration_submitted["top5_duration_submitted_data"]

        return JsonResponse({
            "period": year_period,
            "status_labels": list(status_labels),
            "status_data": status_data,
            "funding_agency_labels": list(funding_agency_labels),
            "funding_agency_data": agency_dataset,
            "lead_unit_labels": lead_unit_labels,
            "lead_unit_data": lead_unit_data,
            "lead_institute_labels": lead_institute_labels,
            "lead_institute_data": lead_institute_data,
            "proposal_lead_labels": proposal_lead_labels,
            "proposal_lead_data": proposal_lead_data,
            "top5_won_valued_labels": top5_won_valued_labels,
            "top5_won_valued_data": top5_won_valued_data,
            "top5_valued_submitted_labels": top5_valued_submitted_labels,
            "top5_valued_submitted_data": top5_valued_submitted_data,
            "top5_duration_won_labels": top5_duration_won_labels,
            "top5_duration_won_data": top5_duration_won_data,
            "top5_duration_submitted_labels": top5_duration_submitted_labels,
            "top5_duration_submitted_data": top5_duration_submitted_data
        })

    def get_status_overview(self, period):
        # Opportunities by Status
        opportunity_status_count = Opportunity.objects.filter(created_at__year=period).values(
            "status", "opp_type").annotate(count=Count("status")).order_by("status")

        chart_data = {}
        opp_status_labels = set()

        for record in opportunity_status_count:
            opp_type = record["opp_type"]
            status = self.status_dict[record["status"]]
            count = record["count"]

            if status not in chart_data:
                chart_data[status] = {}

            chart_data[status][opp_type] = count
            opp_status_labels.add(opp_type)

        report_labels = list(chart_data.keys())

        # Prepare dataset
        opp_dataset = []
        for opp_type in opp_status_labels:
            dataset = {
                "label": opp_type,
                "data": [
                    chart_data.get(status, {}).get(opp_type, 0)
                    for status in report_labels
                ]
            }
            opp_dataset.append(dataset)

        return {
            "status_labels": report_labels,
            "status_data": opp_dataset
        }

    def get_top_10_funding_agencies(self, period):
        top_10 = Opportunity.objects.filter(created_at__year=period, funding_agency__isnull=False).values(
            "funding_agency").annotate(count=Count("id")).order_by("-count")[:10]

        top_ids = [agency["funding_agency"] for agency in top_10]

        funding_agency_counts = Opportunity.objects.filter(
            created_at__year=period,
            funding_agency__in=top_ids
        ).values("funding_agency__code", "status"
                 ).annotate(
            count=Count("id")
        ).order_by("-count", "status")

        chart_data = {}
        agency_status_labels = set()

        for record in funding_agency_counts:
            agency = record["funding_agency__code"]
            status = self.status_dict[record["status"]]
            count = record["count"]

            if agency not in chart_data:
                chart_data[agency] = {}

            chart_data[agency][status] = count
            agency_status_labels.add(status)

        # Convert to chart.js format
        funding_agency_labels = list(chart_data.keys())

        # Prepare dataset
        agency_dataset = []
        for status in agency_status_labels:
            dataset = {
                "label": status,
                "data": [
                    chart_data.get(agency, {}).get(status, 0)
                    for agency in funding_agency_labels
                ]
            }
            agency_dataset.append(dataset)

        return {
            "funding_agency_labels": funding_agency_labels,
            "agency_dataset": agency_dataset
        }

    def get_opportunity_by_lead_unit(self, period):
        opportunities = Opportunity.objects.filter(created_at__year=period, status__gt=1).values(
            "lead_unit__code").annotate(count=Count("id")).order_by("-count")

        return {
            "lead_unit_labels": [opp["lead_unit__code"] for opp in opportunities],
            "lead_unit_data": [opp["count"] for opp in opportunities]
        }

    def get_opportunity_by_lead_institute(self, period):
        opportunities = Opportunity.objects.filter(created_at__year=period, status__gte=5).values(
            "lead_institute__code").annotate(count=Count("id")).order_by("-count")

        return {
            "lead_institute_labels": [opp["lead_institute__code"] for opp in opportunities],
            "lead_institute_data": [opp["count"] for opp in opportunities]
        }

    def get_opportunity_by_proposal_lead(self, period):
        opportunities = Opportunity.objects.filter(created_at__year=period, status__gte=5).values(
            "proposal_lead__first_name").annotate(count=Count("id")).order_by("-count")

        return {
            "proposal_lead_labels": [opp["proposal_lead__first_name"] for opp in opportunities],
            "proposal_lead_data": [opp["count"] for opp in opportunities]
        }

    def get_top5_won_valued_opportunities(self, period):
        opportunities = Opportunity.objects.filter(
            created_at__year=period, status__exact=7, proposal_amount__gt=0).order_by("-proposal_amount")[:5]

        return {
            "top5_won_valued_labels": [opp.funding_agency.code if opp.funding_agency else "unknown" for opp in opportunities],
            "top5_won_valued_data": [opp.proposal_amount for opp in opportunities]
        }

    def get_top5_valued_submitted(self, period):
        opportunities = Opportunity.objects.filter(
            created_at__year=period, status__exact=5, proposal_amount__gt=0).order_by("-proposal_amount")[:5]

        return {
            "top5_valued_submitted_labels": [opp.funding_agency.code if opp.funding_agency else "unknown" for opp in opportunities],
            "top5_valued_submitted_data": [opp.proposal_amount for opp in opportunities]
        }

    def get_top5_duration_opportunities_won(self, period):
        opportunities = Opportunity.objects.filter(
            created_at__year=period, status__exact=7, duration_months__gt=0).order_by("-duration_months")[:5]

        return {
            "top5_duration_won_labels": [opp.funding_agency.code if opp.funding_agency else "unknown" for opp in opportunities],
            "top5_duration_won_data": [opp.duration_months for opp in opportunities]
        }

    def get_top5_duration_submitted(self, period):
        opportunities = Opportunity.objects.filter(
            created_at__year=period, status__exact=5, duration_months__gt=0).order_by("-duration_months")[:5]

        return {
            "top5_duration_submitted_labels": [opp.funding_agency.code if opp.funding_agency else "unknown" for opp in opportunities],
            "top5_duration_submitted_data": [opp.duration_months for opp in opportunities]
        }


def get_total_opportunity_count(request):
    year = request.GET.get("year", now().year)
    result = Opportunity.objects.filter(created_at__year=year).aggregate(
        total_opportunities=Count("id"))

    return HttpResponse(result["total_opportunities"] or 0)


def get_total_submitted_amount(request):
    year = request.GET.get("year", now().year)
    result = Opportunity.objects.filter(created_at__year=year).aggregate(
        total_submitted_amount=Sum(Case(When(status=5, then="proposal_amount"),
                                   default=0,
                                   output_field=IntegerField(),
                                        )))

    return HttpResponse(result["total_submitted_amount"] or 0)


def get_total_won_amount(request):
    year = request.GET.get("year", now().year)
    result = Opportunity.objects.filter(submission_date__year=year).aggregate(
        total_submitted_amount=Sum(Case(When(status=7, then="proposal_amount"),
                                   default=0,
                                   output_field=IntegerField(),
                                        )))

    return HttpResponse(result["total_submitted_amount"] or 0)
