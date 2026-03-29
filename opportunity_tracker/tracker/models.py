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
    pass

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


class Unit(Entity):
    pass

    class Meta:
        db_table = "unit"


class Staff(Person):
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "staff"


class Country(models.Model):
    code = models.CharField(primary_key=True, max_length=5)
    name = models.CharField(max_length=255, blank=False, null=False)

    class Meta:
        db_table = "country"
        verbose_name_plural = "Countries"
        ordering = ["code"]

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

    class Meta:
        db_table = "currency"
        verbose_name_plural = "currencies"

    def __str__(self):
        return self.code


class Opportunity(models.Model):
    OPP_TYPE = [("EOI", "EOI"), ("RFP", "RFP"),
                ("FC", "Fore-cast"), ("NA", "Not Applicable")]
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
        (11, "Transfer to RFP")
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
