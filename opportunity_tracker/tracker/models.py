import os
from typing import Any
from django.db import models
import uuid
from django.contrib.auth.models import User
from django.conf import settings
import re
from django.core.validators import MaxValueValidator
from datetime import timedelta


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, blank=False,
                            null=False, unique=True)
    name = models.CharField(max_length=255, blank=False, null=False)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Person(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, blank=False,
                            null=False, unique=True)
    name = models.CharField(max_length=255, blank=False, null=False)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name


class FundingAgency(Entity):
    AGENCY_TYPE = [
        ("BDA", "Bilateral"),
        ("C", "Corporate"),
        ("F", "Foundation"),
        ("GF", "Global Financing"),
        ("NGO", "NGO"),
        ("UN", "UN")
    ]

    agency_type = models.CharField(
        max_length=3, choices=AGENCY_TYPE, blank=True, null=True)

    class Meta:
        db_table = "funding_agency"
        verbose_name_plural = "Funding Agencies"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_label(self) -> str:
        return f"{self.code} | {self.name}"


class Client(Entity):
    CLIENT_TYPE = [
        ("BDA", "Bilateral Donor Agency"),
        ("DB", "Development Bank"),
        ("F", "Foundation, Philanthropic"),
        ("GHI", "Global Health Initiative"),
        ("O", "Other")
    ]
    client_type = models.CharField(
        max_length=3, choices=CLIENT_TYPE, blank=True, null=True)

    class Meta:
        db_table = "client"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_label(self) -> str:
        return f"{self.code} | {self.name}"


class Institute(Entity):
    pass

    class Meta:
        db_table = "institute"
        ordering = ["name"]
        verbose_name = "Partner Institute"


class Unit(Entity):
    pass

    class Meta:
        db_table = "unit"
        ordering = ["name"]


class Staff(Person):
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "staff"
        ordering = ["name"]


class Country(models.Model):
    code = models.CharField(primary_key=True, max_length=5)
    name = models.CharField(max_length=255, blank=False, null=False)

    class Meta:
        db_table = "country"
        verbose_name_plural = "Countries"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


def get_file_upload_path(instance, filename):
    # Replace all character except a-z, A-Z and 0-9 with _
    foldername = re.sub(r"[^a-zA-Z0-9]", "_", instance.opportunity.ref_no)
    return f"opportunities/{foldername}/{filename}"


class Currency(models.Model):
    code = models.CharField(primary_key=True, max_length=3)
    currency = models.CharField(max_length=50)
    symbol = models.CharField(max_length=3, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "currency"
        verbose_name_plural = "currencies"
        ordering = ["code"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other currencies to false
            Currency.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class GoReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reason = models.CharField(max_length=255, null=False, blank=False)

    class Meta:
        db_table = "go_reason"

    def __str__(self):
        return self.reason


class NoGoReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reason = models.CharField(max_length=255, null=False, blank=False)

    class Meta:
        db_table = "nogo_reason"

    def __str__(self):
        return self.reason


class Opportunity(models.Model):
    OPP_TYPE = [("EOI", "EOI"), ("RFP", "RFP"),
                ("FC", "Fore-cast"), ("NA", "Not Applicable"), ("FA", "Framework Agreement")]
    OPP_STATUS = [
        (1, "Entered"),
        (2, "Go"),
        (3, "NO-Go"),
        (4, "Consider"),
        (5, "Submitted"),
        (6, "Lost"),
        (7, "Won"),
        (8, "Cancelled"),
        (9, "Assumed Lost"),
        (10, "N/A"),
        (11, "Transfer to RFP"),
        (12, "On going"),
        (13, "Finished"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ref_no = models.CharField(
        max_length=50, blank=False, null=False, unique=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    funding_agency = models.ForeignKey(
        FundingAgency, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    opp_type = models.CharField(max_length=3, choices=OPP_TYPE)
    countries = models.ManyToManyField(
        Country, related_name="Opportunities")
    due_date = models.DateField(blank=True, null=True)
    clarification_date = models.DateField(blank=True, null=True)
    intent_bid_date = models.DateField(blank=True, null=True)
    duration_months = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_opportunities")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(
        choices=OPP_STATUS, default=1, null=False, blank=False)
    lead_unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    proposal_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    lead_institute = models.ForeignKey(
        Institute, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    partners = models.ManyToManyField(
        Institute, related_name="partner_Opportunities", blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, blank=True, null=True, related_name="Opportunities")
    proposal_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    net_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    result_note = models.CharField(max_length=300, null=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferred'
    )
    submission_validity = models.PositiveIntegerField(
        blank=True, null=True, validators=[MaxValueValidator(365)])
    result_date = models.DateField(blank=True, null=True)
    is_noncompetitive = models.BooleanField(
        blank=True, null=True, default=False)
    project_start_date = models.DateField(blank=True, null=True)
    project_end_date = models.DateField(blank=True, null=True)
    go_reasons = models.ManyToManyField(
        GoReason, through="OpportunityGoReason", related_name="opportunity_go_reason", null=True, blank=True)
    nogo_reasons = models.ManyToManyField(
        NoGoReason, through="OpportunityNoGoReason", related_name="opportunity_nogo_reason", null=True, blank=True)

    class Meta:
        db_table = "opportunity"
        verbose_name_plural = "Opportunities"

    def __str__(self):
        return self.ref_no

    def get_status_display(self):
        """Override the default get_status_display to show 'Transferred to RFP' for status 11"""
        if self.status == 11:
            return "Transferred to RFP"
        # Call the auto-generated method directly
        return dict(self.OPP_STATUS).get(self.status, str(self.status))

    def get_valid_status_choices(self):
        """Return (id, label) pairs for all statuses in the active workflow.

        Forms use this so the available options always reflect the installed
        workflow definition rather than the hardcoded OPP_STATUS list.
        """
        from tracker.workflows.registry import get_active_workflow
        from tracker.workflows.schema import get_status_choices
        return get_status_choices(get_active_workflow())

    def get_transferred_opportunity(self):
        """Get the RFP opportunity that was created from this opportunity transfer"""
        return self.transferred.first() if self.status == 11 else None

    @property
    def submission_expiry(self):
        """Return the last valid submission date calculated as submission_date + submission_validity days.

        If either value is missing, returns None.
        """
        if self.submission_date and self.submission_validity is not None:
            try:
                return self.submission_date + timedelta(days=int(self.submission_validity))
            except Exception:
                return None
        return None


class OpportunityFile(models.Model):
    opportunity = models.ForeignKey(
        Opportunity, related_name="Files", on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_file_upload_path)

    class Meta:
        db_table = "opportunity_files"

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)

        # Now we will delete the record from the db
        super(OpportunityFile, self).delete(*args, **kwargs)


class OpportunityGoReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    reason = models.ForeignKey(GoReason, on_delete=models.CASCADE)
    other_reason_description = models.CharField(
        max_length=255, blank=True, null=True)

    def __str__(self):
        return self.reason.reason

    class Meta:
        db_table = "opportunity_go_reason"
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "reason"],
                name="unique_opportunity_go_reason"
            )
        ]


class OpportunityNoGoReason(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE)
    reason = models.ForeignKey(NoGoReason, on_delete=models.CASCADE)
    other_reason_description = models.CharField(
        max_length=255, blank=True, null=True)

    def __str__(self):
        return self.reason.reason

    class Meta:
        db_table = "opportunity_nogo_reason"
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "reason"],
                name="unique_opportunity_nogo_reason"
            )
        ]


# Budgeting
class BudgetTemplate(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "budget_template"
        verbose_name = "Budget Template"
        verbose_name_plural = "Budget Templates"

    def __str__(self):
        return self.name


class BudgetTemplateColumn(models.Model):
    template = models.ForeignKey(
        BudgetTemplate,
        on_delete=models.CASCADE,
        related_name="columns"
    )
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    is_readonly = models.BooleanField(default=False)
    display_order = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = "budget_template_column"
        verbose_name = "Budget Template Column"
        verbose_name_plural = "Budget Templates Columns"
        ordering = ["display_order"]
        unique_together = ("template", "key")

    def __str__(self):
        return ""


class BudgetTemplateRow(models.Model):
    ROW_TYPES = [
        ("input", "Input"),
        ("display", "Display"),
        ("total", "Total"),
    ]

    template = models.ForeignKey(
        BudgetTemplate,
        on_delete=models.CASCADE,
        related_name="rows"
    )

    key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    row_type = models.CharField(
        max_length=20,
        choices=ROW_TYPES,
        default="input"
    )
    display_order = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = "budget_template_row"
        verbose_name = "Budget Template Row"
        verbose_name_plural = "Budget Template Rows"
        ordering = ["display_order"]
        unique_together = ("template", "key")

    def __str__(self):
        return ""


class OpportunityBudget(models.Model):
    opportunity = models.OneToOneField(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="budget"
    )

    template = models.ForeignKey(
        BudgetTemplate,
        on_delete=models.PROTECT,
        related_name="opportunity_budget"
    )

    ex_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="opportunity_budget",
        default=Currency.objects.get(is_default=True).pk
    )

    ex_rate_to_default_cur = models.DecimalField(
        max_digits=12,
        decimal_places=6
    )

    class Meta:
        db_table = "opportunity_budget"

    def __str__(self):
        return f"{self.Opportunity.ref_no} - {self.template.name}"


class OpportunityBudgetValue(models.Model):
    budget = models.ForeignKey(
        OpportunityBudget,
        on_delete=models.CASCADE,
        related_name="values"
    )

    row = models.ForeignKey(
        BudgetTemplateRow,
        on_delete=models.PROTECT,
        related_name="budget_values"
    )

    column = models.ForeignKey(
        BudgetTemplateColumn,
        on_delete=models.PROTECT,
        related_name="budget_values"
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        db_table = "budget_value"
        unique_together = ("budget", "row", "column")

    def __str__(self):
        return (
            f"{self.budget.opportunity.ref_no} | "
            f"{self.row.label} | "
            f"{self.column.label}"
        )
