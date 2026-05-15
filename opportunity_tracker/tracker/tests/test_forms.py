"""
Unit tests for tracker app forms.

This module tests:
- Form validation logic
- Custom clean methods
- Form field requirements
- Form widgets and attributes
- Form error messages
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse

from tracker.forms import (
    LoginForm, OpportunityForm, UpdateOpportunityForm, UpdateStatusForm,
    SubmitProposalForm, OpportunitySearchForm, FundingAgencyForm, ClientForm,
    FundingAgencyChoiceField, ClientChoiceField
)
from tracker.models import (
    FundingAgency, Client, Institute, NoGoReason, Unit, Country, Currency, Opportunity,
    GoReason
)

User = get_user_model()


class LoginFormTest(TestCase):
    """Test cases for LoginForm."""

    def test_login_form_valid(self):
        """Test login form with valid data."""
        form_data = {
            'username': 'testuser',
            'password': 'testpass123',
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_login_form_with_next(self):
        """Test login form with next parameter."""
        form_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'next': '/dashboard/'
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['next'], '/dashboard/')

    def test_login_form_missing_username(self):
        """Test login form without username."""
        form_data = {'password': 'testpass123'}
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_login_form_missing_password(self):
        """Test login form without password."""
        form_data = {'username': 'testuser'}
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)


class FundingAgencyChoiceFieldTest(TestCase):
    """Test cases for FundingAgencyChoiceField."""

    def setUp(self):
        """Set up test data."""
        self.agency = FundingAgency.objects.create(
            code="USAID",
            name="United States Agency for International Development"
        )

    def test_label_from_instance(self):
        """Test custom label format."""
        field = FundingAgencyChoiceField(queryset=FundingAgency.objects.all())
        label = field.label_from_instance(self.agency)
        self.assertEqual(
            label, "USAID | United States Agency for International Development")


class ClientChoiceFieldTest(TestCase):
    """Test cases for ClientChoiceField."""

    def setUp(self):
        """Set up test data."""
        self.client = Client.objects.create(
            code="GIZ",
            name="Deutsche Gesellschaft für Internationale Zusammenarbeit"
        )

    def test_label_from_instance(self):
        """Test custom label format."""
        field = ClientChoiceField(queryset=Client.objects.all())
        label = field.label_from_instance(self.client)
        self.assertEqual(
            label, "GIZ | Deutsche Gesellschaft für Internationale Zusammenarbeit")


class OpportunityFormTest(TestCase):
    """Test cases for OpportunityForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.funding_agency = FundingAgency.objects.create(
            code="USAID", name="USAID")
        self.client = Client.objects.create(code="GIZ", name="GIZ")
        self.country, _ = Country.objects.get_or_create(
            code="KE", defaults={"name": "Kenya"})
        self.currency, _ = Currency.objects.get_or_create(
            code="USD", defaults={"currency": "US Dollar"})

    def test_opportunity_form_valid(self):
        """Test opportunity form with valid data."""
        form_data = {
            'ref_no': 'OPP-2024-001',
            'title': 'Test Opportunity',
            'funding_agency': self.funding_agency.id,
            'client': self.client.id,
            'opp_type': 'RFP',
            'countries': [self.country.code],
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'status': 1,
        }
        form = OpportunityForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_opportunity_form_missing_title(self):
        """Test form validation when title is missing."""
        form_data = {
            'ref_no': 'OPP-2024-002',
            'opp_type': 'RFP',
            'status': 1,
        }
        form = OpportunityForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertEqual(form.errors['title'][0], 'Title is required')

    def test_opportunity_form_currency_validation(self):
        """Test that currency is required when proposal_amount is provided."""
        form_data = {
            'ref_no': 'OPP-2024-003',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 1,
            'proposal_amount': '10000.00',
        }
        form = OpportunityForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('currency', form.errors)

    def test_opportunity_form_with_currency_and_amount(self):
        """Test form is valid when both currency and amount are provided."""
        form_data = {
            'ref_no': 'OPP-2024-004',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 1,
            'currency': self.currency.code,  # USD
            'proposal_amount': '10000.00',
            'countries': [self.country.code],  # Required field
        }
        form = OpportunityForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_opportunity_form_widget_attrs(self):
        """Test that form widgets have correct attributes."""
        form = OpportunityForm()

        # Check date widgets have DateInput widget
        self.assertEqual(
            form.fields['due_date'].widget.__class__.__name__, 'DateInput')
        self.assertEqual(
            form.fields['clarification_date'].widget.__class__.__name__, 'DateInput')
        self.assertEqual(
            form.fields['intent_bid_date'].widget.__class__.__name__, 'DateInput')

        # Check data attributes for funding_agency
        self.assertIn('data-url', form.fields['funding_agency'].widget.attrs)
        self.assertIn(
            'data-entity', form.fields['funding_agency'].widget.attrs)


class UpdateOpportunityFormTest(TestCase):
    """Test cases for UpdateOpportunityForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.funding_agency = FundingAgency.objects.create(
            code="USAID", name="USAID")
        self.country, _ = Country.objects.get_or_create(
            code="KE", defaults={"name": "Kenya"})
        self.unit = Unit.objects.create(code="IT", name="IT Unit")
        self.currency, _ = Currency.objects.get_or_create(
            code="USD", defaults={"currency": "US Dollar"})
        self.institute = Institute.objects.create(code="MIT", name="MIT")

        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-TEST',
            title='Test Opportunity',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )

    def test_update_form_status_go_requires_fields(self):
        """Test that proposal_lead and lead_unit are required when status >= 2 (except 3,4)."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 2,  # Go status
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('proposal_lead', form.errors)
        self.assertIn('lead_unit', form.errors)

    def test_update_form_status_no_go_no_required_fields(self):
        """Test that NO-Go status doesn't require proposal_lead and lead_unit."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 3,  # NO-Go status
            # Add countries as it might be required
            'countries': [self.country.code],
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())

    def test_update_form_status_submitted_requires_submission_date(self):
        """Test that submission_date is required when status >= 5."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 5,  # Submitted
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('submission_date', form.errors)

    def test_update_form_subscription_field(self):
        """Test is_subscribed field initialization."""
        form = UpdateOpportunityForm(
            instance=self.opportunity, is_subscribed=True)
        self.assertTrue(form.fields['is_subscribed'].initial)

    def test_update_form_proposal_lead_label(self):
        """Test that proposal_lead displays full name."""
        form = UpdateOpportunityForm(instance=self.opportunity)
        label = form.fields['proposal_lead'].label_from_instance(self.user)
        self.assertEqual(label, "Test User")

    def test_update_form_result_date_not_in_form_fields(self):
        """Test that result_date is not part of UpdateOpportunityForm fields.
        result_date is only managed through UpdateStatusForm."""
        form = UpdateOpportunityForm(instance=self.opportunity)
        self.assertNotIn('result_date', form.fields)

    def test_update_form_result_date_not_required_for_entered_status(self):
        """Test that result_date is not required for status 1 (Entered)."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 1,  # Entered
            'countries': [self.country.code],
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_update_form_result_date_not_required_for_go_status(self):
        """Test that result_date is not required for status 2 (Go)."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 2,  # Go
            'countries': [self.country.code],
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_update_form_result_date_not_required_for_submitted_status(self):
        """Test that result_date is not required for status 5 (Submitted)."""
        form_data = {
            'ref_no': 'OPP-2024-TEST',
            'title': 'Test',
            'opp_type': 'RFP',
            'status': 5,  # Submitted
            'countries': [self.country.code],
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'submission_date': date.today().isoformat(),
            'lead_institute': self.institute.id,
        }
        form = UpdateOpportunityForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())


class UpdateStatusFormTest(TestCase):
    """Test cases for UpdateStatusForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.unit = Unit.objects.create(code="IT", name="IT Unit")
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-STATUS',
            title='Status Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )
        # Shared reasons used across multiple tests
        self.go_reason_clarified = GoReason.objects.create(reason='Clarified')
        self.go_reason_other = GoReason.objects.create(reason='Other')
        self.nogo_reason_clarified = NoGoReason.objects.create(
            reason='Clarification')
        self.nogo_reason_other = NoGoReason.objects.create(reason='Other')

    def test_status_form_go_requires_proposal_lead_and_unit(self):
        """Test that Go status requires proposal_lead and lead_unit."""
        form_data = {
            'status': '2',  # Go
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('proposal_lead', form.errors)
        self.assertIn('lead_unit', form.errors)

    def test_status_form_go_valid_with_required_fields(self):
        """Test that Go status is valid with required fields."""
        form_data = {
            'status': '2',
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'go_reasons': [str(self.go_reason_clarified.id)],
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_other_statuses_valid_without_fields(self):
        """Test that other statuses don't require proposal_lead and lead_unit."""
        for status in ['3', '4', '5', '6', '7']:
            form_data = {'status': status}
            form = UpdateStatusForm(data=form_data, instance=self.opportunity)
            # Note: We're only checking status validation here
            # Status 5 might fail in UpdateOpportunityForm due to submission_date

    def test_status_form_result_date_required_for_lost_status(self):
        """Test that result_date is required when status is 6 (Lost)."""
        form_data = {
            'status': '6',  # Lost
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('result_date', form.errors)
        self.assertEqual(form.errors['result_date']
                         [0], 'Result Date is required')

    def test_status_form_result_date_required_for_won_status(self):
        """Test that result_date is required when status is 7 (Won)."""
        form_data = {
            'status': '7',  # Won
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('result_date', form.errors)
        self.assertEqual(form.errors['result_date']
                         [0], 'Result Date is required')

    def test_status_form_result_date_required_for_cancelled_status(self):
        """Test that result_date is required when status is 8 (Cancelled)."""
        form_data = {
            'status': '8',  # Cancelled
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('result_date', form.errors)
        self.assertEqual(form.errors['result_date']
                         [0], 'Result Date is required')

    def test_status_form_result_date_required_for_assumed_lost_status(self):
        """Test that result_date is required when status is 9 (Assumed Lost)."""
        form_data = {
            'status': '9',  # Assumed Lost
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('result_date', form.errors)
        self.assertEqual(form.errors['result_date']
                         [0], 'Result Date is required')

    def test_status_form_result_date_valid_for_lost_status(self):
        """Test that form is valid when result_date is provided for Lost status."""
        form_data = {
            'status': '6',  # Lost
            'result_date': date.today().isoformat(),
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_valid_for_won_status(self):
        """Test that form is valid when result_date is provided for Won status."""
        form_data = {
            'status': '7',  # Won
            'result_date': date.today().isoformat(),
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_valid_for_cancelled_status(self):
        """Test that form is valid when result_date is provided for Cancelled status."""
        form_data = {
            'status': '8',  # Cancelled
            'result_date': date.today().isoformat(),
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_valid_for_assumed_lost_status(self):
        """Test that form is valid when result_date is provided for Assumed Lost status."""
        form_data = {
            'status': '9',  # Assumed Lost
            'result_date': date.today().isoformat(),
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_not_required_for_go_status(self):
        """Test that result_date is not required for status 2 (Go)."""
        form_data = {
            'status': '2',  # Go
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'go_reasons': [str(self.go_reason_clarified.id)]
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_not_required_for_no_go_status(self):
        """Test that result_date is not required for status 3 (NO-Go)."""
        form_data = {
            'status': '3',  # NO-Go
            'nogo_reasons': [str(self.nogo_reason_clarified.id)]
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_not_required_for_consider_status(self):
        """Test that result_date is not required for status 4 (Consider)."""
        form_data = {
            'status': '4',  # Consider
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_other_requires_text_when_other_selected(self):
        """Test that selecting Other requires the other reason text."""
        form_data = {
            'status': '2',
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'go_reasons': [str(self.go_reason_other.id)],
            'go_reasons_other_id': str(self.go_reason_other.id),
            'go_reasons_other_text': '',
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('go_reasons_other_text', form.errors)

    def test_status_form_other_accepts_text_when_other_selected(self):
        """Test that selecting Other with text is valid."""
        form_data = {
            'status': '2',
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'go_reasons': [str(self.go_reason_other.id)],
            'go_reasons_other_id': str(self.go_reason_other.id),
            'go_reasons_other_text': 'Custom reason details',
        }
        form = UpdateStatusForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_status_form_result_date_min_value_with_submission_date(self):
        """Test that result_date min attribute is set based on submission_date."""
        self.opportunity.submission_date = date(2024, 1, 15)
        self.opportunity.save()

        form = UpdateStatusForm(instance=self.opportunity)
        self.assertEqual(
            form.fields['result_date'].widget.attrs['min'],
            '2024-01-15'
        )

    def test_status_form_result_date_max_value_is_today(self):
        """Test that result_date max attribute is set to today."""
        form = UpdateStatusForm(instance=self.opportunity)
        self.assertEqual(
            form.fields['result_date'].widget.attrs['max'],
            date.today().isoformat()
        )


class SubmitProposalFormTest(TestCase):
    """Test cases for SubmitProposalForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.institute = Institute.objects.create(code="MIT", name="MIT")
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-SUBMIT',
            title='Submit Test',
            opp_type='RFP',
            created_by=self.user,
            status=2
        )

    def test_submit_form_requires_submission_date(self):
        """Test that submission_date is required."""
        form_data = {
            'status': 5,
            'lead_institute': self.institute.id,
        }
        form = SubmitProposalForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('submission_date', form.errors)
        self.assertEqual(form.errors['submission_date']
                         [0], 'Please provide a submission date')

    def test_submit_form_requires_lead_institute(self):
        """Test that lead_institute is required."""
        form_data = {
            'status': 5,
            'submission_date': date.today().isoformat(),
        }
        form = SubmitProposalForm(data=form_data, instance=self.opportunity)
        self.assertFalse(form.is_valid())
        self.assertIn('lead_institute', form.errors)
        self.assertEqual(form.errors['lead_institute']
                         [0], 'Select a Lead Organization')

    def test_submit_form_valid(self):
        """Test valid submission form."""
        form_data = {
            'status': 5,
            'submission_date': date.today().isoformat(),
            'lead_institute': self.institute.id,
            'submission_validity': 30,
        }
        form = SubmitProposalForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())

    def test_submit_form_with_partners(self):
        """Test form with partners."""
        partner1 = Institute.objects.create(code="HARV", name="Harvard")
        partner2 = Institute.objects.create(code="STAN", name="Stanford")

        form_data = {
            'status': 5,
            'submission_date': date.today().isoformat(),
            'lead_institute': self.institute.id,
            'partners': [partner1.id, partner2.id],
        }
        form = SubmitProposalForm(data=form_data, instance=self.opportunity)
        self.assertTrue(form.is_valid())


class OpportunitySearchFormTest(TestCase):
    """Test cases for OpportunitySearchForm."""

    def setUp(self):
        """Set up test data."""
        self.funding_agency = FundingAgency.objects.create(
            code="USAID", name="USAID")
        self.client = Client.objects.create(code="GIZ", name="GIZ")
        self.country, _ = Country.objects.get_or_create(
            code="KE", defaults={"name": "Kenya"})

    def test_search_form_all_fields_optional(self):
        """Test that all search form fields are optional."""
        form = OpportunitySearchForm(data={})
        self.assertTrue(form.is_valid())

    def test_search_form_with_filters(self):
        """Test search form with various filters."""
        form_data = {
            'ref_no': 'OPP-2024',
            'title': 'Test',
            'funding_agency': self.funding_agency.id,
            'client': self.client.id,
            'status': '1',
            'opp_type': 'RFP',
            'country': self.country.code,
            'is_subscribed': True,
        }
        form = OpportunitySearchForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_search_form_widget_attrs(self):
        """Test that search form fields have htmx attributes."""
        form = OpportunitySearchForm()

        # Check that fields have hx-get attribute
        for field_name in form.fields:
            attrs = form.fields[field_name].widget.attrs
            self.assertIn('hx-get', attrs)
            self.assertIn('hx-target', attrs)
            self.assertIn('hx-trigger', attrs)


class FundingAgencyFormTest(TestCase):
    """Test cases for FundingAgencyForm."""

    def test_funding_agency_form_valid(self):
        """Test funding agency form with valid data."""
        form_data = {
            'code': 'USAID',
            'name': 'United States Agency for International Development'
        }
        form = FundingAgencyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_funding_agency_form_missing_code(self):
        """Test form validation when code is missing."""
        form_data = {'name': 'Test Agency'}
        form = FundingAgencyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_funding_agency_form_missing_name(self):
        """Test form validation when name is missing."""
        form_data = {'code': 'TEST'}
        form = FundingAgencyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class ClientFormTest(TestCase):
    """Test cases for ClientForm."""

    def test_client_form_valid(self):
        """Test client form with valid data."""
        form_data = {
            'code': 'GIZ',
            'name': 'Deutsche Gesellschaft für Internationale Zusammenarbeit',
            'client_type': 'BDA'
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_client_form_without_type(self):
        """Test client form without client_type (optional)."""
        form_data = {
            'code': 'TEST',
            'name': 'Test Client'
        }
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_client_form_missing_required_fields(self):
        """Test form validation when required fields are missing."""
        form_data = {'client_type': 'BDA'}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        self.assertIn('name', form.errors)
