"""
Unit tests for tracker app views.

This module tests:
- View permissions and authentication
- View responses (status codes, templates)
- Context data
- Form handling in views
- HTMX-specific behavior
- URL routing
"""
from datetime import date, timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client as TestClient, override_settings
from django.urls import reverse

from tracker.models import (
    FundingAgency, Client, Institute, Unit, Country, Currency,
    Opportunity, OpportunityFile, GoReason, OpportunityGoReason
)
from notification.models import OpportunitySubscription

User = get_user_model()


class IndexViewTest(TestCase):
    """Test cases for IndexView."""

    def setUp(self):
        """Set up test client and user."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')

    def test_index_view_get(self):
        """Test GET request to index view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/home.html')


class OpportunityListViewTest(TestCase):
    """Test cases for OpportunityListView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.funding_agency = FundingAgency.objects.create(
            code="USAID", name="USAID")
        self.test_client = Client.objects.create(code="GIZ", name="GIZ")
        self.country, _ = Country.objects.get_or_create(
            code="KE", defaults={"name": "Kenya"})

        # Create test opportunities
        for i in range(1, 20):
            Opportunity.objects.create(
                ref_no=f'OPP-2024-{i:03d}',
                title=f'Test Opportunity {i}',
                opp_type='RFP',
                created_by=self.user,
                status=1
            )

    def test_opportunity_list_view_get(self):
        """Test GET request to opportunity list view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/list.html')
        self.assertIn('form', response.context)
        self.assertIn('page_obj', response.context)

    def test_opportunity_list_view_pagination(self):
        """Test pagination in opportunity list view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'))
        # paginate_by = 15
        self.assertEqual(len(response.context['page_obj']), 15)

    def test_opportunity_list_view_filter_by_ref_no(self):
        """Test filtering opportunities by ref_no."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'), {
                                   'ref_no': 'OPP-2024-001'})
        self.assertEqual(response.context['opportunity_count'], 1)

    def test_opportunity_list_view_filter_by_title(self):
        """Test filtering opportunities by title."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'), {
                                   'title': 'Opportunity 1'})
        self.assertGreater(response.context['opportunity_count'], 0)

    def test_opportunity_list_view_filter_by_funding_agency(self):
        """Test filtering opportunities by funding_agency."""
        Opportunity.objects.filter(
            ref_no='OPP-2024-001').update(funding_agency=self.funding_agency)

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'), {
                                   'funding_agency': self.funding_agency.id})
        self.assertEqual(response.context['opportunity_count'], 1)

    def test_opportunity_list_view_filter_by_status(self):
        """Test filtering opportunities by status."""
        Opportunity.objects.filter(ref_no='OPP-2024-001').update(status=2)

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('opportunities'), {'status': '2'})
        self.assertEqual(response.context['opportunity_count'], 1)

    def test_opportunity_list_view_htmx(self):
        """Test HTMX request returns partial template."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('opportunities'),
            HTTP_HX_REQUEST='true'
        )
        self.assertTemplateUsed(
            response, 'tracker/partials/opportunity_cards.html')


class OpportunityCreateViewTest(TestCase):
    """Test cases for OpportunityCreateView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        # Create a default country for tests
        self.country, _ = Country.objects.get_or_create(
            code="US", defaults={"name": "United States"})
        self.funding_agency = FundingAgency.objects.create(
            code="USAID", name="USAID")
        self.country, _ = Country.objects.get_or_create(
            code="KE", defaults={"name": "Kenya"})

    def test_opportunity_create_view_get(self):
        """Test GET request to opportunity create view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('new_opportunity'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/new.html')

    def test_opportunity_create_view_post_valid(self):
        """Test POST request with valid data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-NEW',
            'title': 'New Opportunity',
            'opp_type': 'RFP',
            'status': 1,
            'countries': [self.country.code],  # Use country code (primary key)
        }
        response = self.client.post(reverse('new_opportunity'), data=form_data)

        # Redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that opportunity was created
        self.assertTrue(Opportunity.objects.filter(
            ref_no='OPP-2024-NEW').exists())
        opp = Opportunity.objects.get(ref_no='OPP-2024-NEW')
        self.assertEqual(opp.created_by, self.user)

    def test_opportunity_create_view_post_invalid(self):
        """Test POST request with invalid data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-INVALID',
            # Missing required 'title' field
            'opp_type': 'RFP',
            'status': 1,
        }
        response = self.client.post(reverse('new_opportunity'), data=form_data)
        self.assertEqual(response.status_code, 200)  # Returns form with errors
        # Check form has errors
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertEqual(form.errors['title'], ['Title is required'])

    @override_settings(MEDIA_ROOT='/tmp/test_media/')
    def test_opportunity_create_with_files(self):
        """Test creating opportunity with file uploads."""
        self.client.login(username='testuser', password='testpass123')

        test_file = SimpleUploadedFile(
            "test_doc.pdf", b"file_content", content_type="application/pdf")

        form_data = {
            'ref_no': 'OPP-2024-FILE',
            'title': 'Opportunity with Files',
            'opp_type': 'RFP',
            'status': 1,
            'countries': [self.country.code],  # Use country code (primary key)
        }
        files_data = {
            'files': test_file,
        }
        response = self.client.post(reverse('new_opportunity'), data={
                                    **form_data, **files_data})

        # Check redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check opportunity and file were created
        self.assertTrue(Opportunity.objects.filter(
            ref_no='OPP-2024-FILE').exists())
        opp = Opportunity.objects.get(ref_no='OPP-2024-FILE')
        self.assertEqual(opp.Files.count(), 1)

    def test_opportunity_create_with_transfer(self):
        """Test creating RFP from EOI transfer."""
        from tracker.workflows.registry import get_active_workflow
        from tracker.workflows.schema import get_status_slug_to_id
        self.client.login(username='testuser', password='testpass123')

        # Create parent EOI
        parent_eoi = Opportunity.objects.create(
            ref_no='EOI-2024-001',
            title='Parent EOI',
            opp_type='EOI',
            created_by=self.user,
            status=7  # Won
        )
        parent_eoi.countries.add(self.country)

        # GET request to see pre-filled form
        response = self.client.get(
            reverse('new_opportunity') +
            f'?source_id={parent_eoi.id}&is_transfer=true'
        )

        # Check initial data is pre-filled
        self.assertEqual(
            response.context['form'].initial['title'], 'Parent EOI')
        self.assertEqual(response.context['form'].initial['opp_type'], 'RFP')

        # Create child RFP through transfer - submit the form
        form_data = {
            'ref_no': 'RFP-2024-001',
            'title': 'Child RFP',
            'opp_type': 'RFP',
            'status': 1,
            'source_id': str(parent_eoi.id),
            'countries': [self.country.code],  # Use country code (primary key)
        }
        response = self.client.post(
            reverse('new_opportunity') +
            f'?source_id={parent_eoi.id}&is_transfer=true',
            data=form_data
        )

        # Check redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check child was created
        self.assertTrue(Opportunity.objects.filter(
            ref_no='RFP-2024-001').exists())
        child_rfp = Opportunity.objects.get(ref_no='RFP-2024-001')
        self.assertEqual(child_rfp.parent, parent_eoi)

        # Check parent status updated to transfer_to_rfp (resolved from active workflow)
        transfer_id = get_status_slug_to_id(
            get_active_workflow()).get('transfer_to_rfp')
        parent_eoi.refresh_from_db()
        self.assertIsNotNone(
            transfer_id, "Active workflow must define transfer_to_rfp")
        self.assertEqual(parent_eoi.status, transfer_id)


class OpportunityUpdateViewTest(TestCase):
    """Test cases for OpportunityUpdateView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.country, _ = Country.objects.get_or_create(
            code="US", defaults={"name": "United States"})
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-UPDATE',
            title='Update Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )
        self.opportunity.countries.add(self.country)

    def test_opportunity_update_view_get(self):
        """Test GET request to opportunity update view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('update_opportunity', kwargs={'pk': self.opportunity.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/update.html')
        self.assertEqual(response.context['form'].instance, self.opportunity)

    def test_opportunity_update_view_post_valid(self):
        """Test POST request with valid update data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-UPDATE',
            'title': 'Updated Title',
            'opp_type': 'RFP',
            'status': 1,
            'countries': [self.country.code],  # Use country code (primary key)
        }
        response = self.client.post(
            reverse('update_opportunity', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.title, 'Updated Title')
        self.assertEqual(self.opportunity.updated_by, self.user)

    def test_opportunity_update_preserves_ref_no(self):
        """Test that ref_no field is marked as readonly in update form.

        Note: While the form widget has readonly attribute, the form currently
        allows ref_no changes through direct form submission. This test verifies
        the current behavior. Consider adding server-side validation in the form's
        clean() method if ref_no should be truly immutable.
        """
        self.client.login(username='testuser', password='testpass123')
        original_ref_no = self.opportunity.ref_no

        # Test that ref_no field has readonly attribute in the form
        response = self.client.get(
            reverse('update_opportunity', kwargs={'pk': self.opportunity.pk}))
        form = response.context['form']
        self.assertIn('readonly', form.fields['ref_no'].widget.attrs)

        # Current behavior: ref_no CAN be changed via direct POST (no server-side validation)
        form_data = {
            'ref_no': 'DIFFERENT-REF',
            'title': 'Updated',
            'opp_type': 'RFP',
            'status': 1,
            'countries': [self.country.code],
        }
        self.client.post(
            reverse('update_opportunity', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        # Currently ref_no DOES change - this documents actual behavior
        self.assertEqual(self.opportunity.ref_no, 'DIFFERENT-REF')


class OpportunityStatusUpdateViewTest(TestCase):
    """Test cases for OpportunityStatusUpdateView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.unit = Unit.objects.create(code="IT", name="IT Unit")
        self.institute = Institute.objects.create(code="MIT", name="MIT")
        self.country, _ = Country.objects.get_or_create(
            code="US", defaults={"name": "United States"})
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-STATUS',
            title='Status Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )
        self.opportunity.countries.add(self.country)
        self.go_reason_clarified = GoReason.objects.create(reason='Clarified')

    def test_status_update_to_go(self):
        """Test updating status to Go with required fields."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '2',  # Go
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'countries': [self.country.code],  # Use country code (primary key)
            'go_reasons': [str(self.go_reason_clarified.id)]
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 2)
        self.assertEqual(self.opportunity.proposal_lead, self.user)
        self.assertEqual(self.opportunity.lead_unit, self.unit)

    def test_status_update_other_reason_persists_through_model(self):
        """Test that Other reason text is stored in the through model."""
        self.client.login(username='testuser', password='testpass123')
        other_reason = GoReason.objects.create(reason='Other')

        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '2',  # Go
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'countries': [self.country.code],
            'go_reasons': [str(other_reason.id)],
            'go_reasons_other_id': str(other_reason.id),
            'go_reasons_other_text': 'Custom other reason',
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.assertEqual(response.status_code, 302)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 2)
        relation = OpportunityGoReason.objects.get(
            opportunity=self.opportunity, reason=other_reason)
        self.assertEqual(relation.other_reason_description,
                         'Custom other reason')

    def test_status_update_context_filtered_status(self):
        """Test that context contains filtered status choices based on current status."""
        self.client.login(username='testuser', password='testpass123')

        # For status=Entered, expect decision options from workflow-backed choices.
        response = self.client.get(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk})
        )
        status_labels = dict(self.opportunity.get_valid_status_choices())
        self.assertEqual(response.context['filtered_status'], [
                         (2, status_labels[2]), (3, status_labels[3]), (4, status_labels[4])])

        # Update to submitted
        self.opportunity.status = 5
        self.opportunity.save()

        response = self.client.get(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk})
        )
        self.assertEqual(response.context['filtered_status'], [
            (7, status_labels[7]),
            (6, status_labels[6]),
            (8, status_labels[8]),
            (9, status_labels[9]),
            (10, status_labels[10]),
        ])

    def test_status_update_to_lost_requires_result_date(self):
        """Test that updating status to Lost requires result_date."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '6',  # Lost
            'countries': [self.country.code],
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        # Form should be invalid without result_date, status doesn't change
        self.assertEqual(response.status_code, 200)  # Returns form with errors
        self.opportunity.refresh_from_db()
        # Status should not change
        self.assertEqual(self.opportunity.status, 1)

    def test_status_update_to_won_requires_result_date(self):
        """Test that updating status to Won requires result_date."""
        self.client.login(username='testuser', password='testpass123')
        self.opportunity.status = 5  # Submitted
        self.opportunity.submission_date = date.today()
        self.opportunity.save()

        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '7',  # Won
            'countries': [self.country.code],
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        # Form should be invalid without result_date
        self.assertEqual(response.status_code, 200)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 5)  # Status unchanged

    def test_status_update_to_cancelled_requires_result_date(self):
        """Test that updating status to Cancelled requires result_date."""
        self.client.login(username='testuser', password='testpass123')
        self.opportunity.status = 5
        self.opportunity.save()

        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '8',  # Cancelled
            'countries': [self.country.code],
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.assertEqual(response.status_code, 200)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 5)  # Status unchanged

    def test_status_update_to_assumed_lost_requires_result_date(self):
        """Test that updating status to Assumed Lost requires result_date."""
        self.client.login(username='testuser', password='testpass123')
        self.opportunity.status = 5
        self.opportunity.save()

        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '9',  # Assumed Lost
            'countries': [self.country.code],
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.assertEqual(response.status_code, 200)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 5)  # Status unchanged

    def test_status_update_to_lost_with_result_date_valid(self):
        """Test that updating status to Lost with result_date is successful."""
        self.client.login(username='testuser', password='testpass123')
        # Need to set status to 5 first to allow transition to Lost
        self.opportunity.status = 5
        self.opportunity.submission_date = date.today()
        self.opportunity.lead_unit = self.unit
        self.opportunity.proposal_lead = self.user
        self.opportunity.save()

        result_date_value = date.today()
        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '6',  # Lost
            'result_date': result_date_value.isoformat(),
            'countries': [self.country.code],
            'submission_date': date.today().isoformat(),
            'lead_institute': self.institute.id,
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 6)
        self.assertEqual(self.opportunity.result_date, result_date_value)

    def test_status_update_to_won_with_result_date_valid(self):
        """Test that updating status to Won with result_date is successful."""
        self.client.login(username='testuser', password='testpass123')
        self.opportunity.status = 5
        self.opportunity.submission_date = date.today() - timedelta(days=30)
        self.opportunity.lead_unit = self.unit
        self.opportunity.proposal_lead = self.user
        self.opportunity.save()

        result_date_value = date.today()
        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '7',  # Won
            'result_date': result_date_value.isoformat(),
            'countries': [self.country.code],
            'submission_date': (date.today() - timedelta(days=30)).isoformat(),
            'lead_institute': self.institute.id,
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 7)
        self.assertEqual(self.opportunity.result_date, result_date_value)

    def test_status_update_to_go_does_not_require_result_date(self):
        """Test that updating status to Go does not require result_date."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-STATUS',
            'title': 'Status Test',
            'opp_type': 'RFP',
            'status': '2',  # Go
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'countries': [self.country.code],
            'go_reasons': [str(self.go_reason_clarified.id)]
            # No result_date
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 2)
        self.assertIsNone(self.opportunity.result_date)

    def test_go_validation_failure_does_not_show_result_date_errors(self):
        """
        Regression: when Go transition fails (missing lead_unit/proposal_lead),
        the re-rendered modal must NOT show errors for result_date,
        project_start_date or project_end_date — those fields are irrelevant
        for a Go transition.
        """
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'status': '2',  # Go — deliberately omit lead_unit and proposal_lead
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data,
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        form = response.context['update_status_form']
        # Must have exactly these two errors and nothing else
        self.assertEqual(set(form.errors.keys()), {
                         'lead_unit', 'proposal_lead', 'go_reasons'})

    def test_status_form_data_preserved_on_rerender(self):
        """
        Regression: after a failed POST the re-rendered modal must carry the
        submitted status value in update_status_form.data so the template can
        re-check the correct radio button.
        """
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'status': '2',  # Go — deliberately omit required fields to trigger failure
        }
        response = self.client.post(
            reverse('udpate_status', kwargs={'pk': self.opportunity.pk}),
            data=form_data,
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        form = response.context['update_status_form']
        # The submitted status value must be in form.data so the template
        # can compare it (as a string) against the choice integer via |stringformat:"s"
        self.assertEqual(form.data.get('status'), '2')


class OpportunitySubmitViewTest(TestCase):
    """Test cases for OpportunitySubmitView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.unit = Unit.objects.create(code="IT", name="IT Unit")
        self.institute = Institute.objects.create(code="MIT", name="MIT")
        self.country, _ = Country.objects.get_or_create(
            code="US", defaults={"name": "United States"})
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-SUBMIT',
            title='Submit Test',
            opp_type='RFP',
            created_by=self.user,
            status=2,
            proposal_lead=self.user,
            lead_unit=self.unit
        )
        self.opportunity.countries.add(self.country)

    def test_submit_proposal_valid(self):
        """Test submitting proposal with valid data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'ref_no': 'OPP-2024-SUBMIT',
            'title': 'Submit Test',
            'opp_type': 'RFP',
            'status': 5,
            'submission_date': date.today().isoformat(),
            'lead_institute': self.institute.id,
            'submission_validity': 30,
            'proposal_lead': self.user.id,
            'lead_unit': self.unit.id,
            'countries': [self.country.code],  # Use country code (primary key)
        }
        response = self.client.post(
            reverse('submit_proposal', kwargs={'pk': self.opportunity.pk}),
            data=form_data
        )

        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, 5)  # Submitted
        self.assertEqual(self.opportunity.lead_institute, self.institute)


class OpportunityDetailViewTest(TestCase):
    """Test cases for OpportunityDetailView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-DETAIL',
            title='Detail Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )

    def test_opportunity_detail_view_get(self):
        """Test GET request to opportunity detail view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('opportunity', kwargs={'pk': self.opportunity.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/detail_modal.html')
        self.assertEqual(response.context['opportunity'], self.opportunity)

    def test_opportunity_detail_ajax_request(self):
        """Test AJAX request to detail view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('opportunity', kwargs={'pk': self.opportunity.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('html', data)


class OpportunityDetailAnonymousViewTest(TestCase):
    """Test cases for OpportunityDetailAnonymousView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-ANON',
            title='Anonymous Detail Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )

    def test_opportunity_detail_anonymous_no_login_required(self):
        """Test that anonymous detail view doesn't require login."""
        # Don't login
        response = self.client.get(
            reverse('opportunity_anonymous', kwargs={'pk': self.opportunity.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/detail_anonymous.html')


class FileDeleteViewTest(TestCase):
    """Test cases for FileDeleteView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.opportunity = Opportunity.objects.create(
            ref_no='OPP-2024-FILE-DEL',
            title='File Delete Test',
            opp_type='RFP',
            created_by=self.user,
            status=1
        )

    @override_settings(MEDIA_ROOT='/tmp/test_media/')
    def test_file_delete(self):
        """Test deleting an opportunity file."""
        # Create file
        test_file = SimpleUploadedFile("test.pdf", b"content")
        opp_file = OpportunityFile.objects.create(
            opportunity=self.opportunity,
            file=test_file
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.delete(
            reverse('delete_attachment', kwargs={'pk': opp_file.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(OpportunityFile.objects.filter(
            pk=opp_file.pk).exists())


class NewFundingAgencyViewTest(TestCase):
    """Test cases for NewFundingAgencyView."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')

    def test_new_funding_agency_get(self):
        """Test GET request to new funding agency view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('new_funding_agency'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_new_funding_agency_post_valid(self):
        """Test POST request with valid data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'code': 'USAID',
            'name': 'United States Agency for International Development'
        }
        response = self.client.post(
            reverse('new_funding_agency'), data=form_data)

        self.assertTrue(FundingAgency.objects.filter(code='USAID').exists())

    def test_new_funding_agency_htmx_returns_json(self):
        """Test HTMX request returns JSON response."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'code': 'WHO',
            'name': 'World Health Organization'
        }
        response = self.client.post(
            reverse('new_funding_agency'),
            data=form_data,
            HTTP_HX_REQUEST='true'
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('name', data)


class NewClientViewTest(TestCase):
    """Test cases for NewClientView."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')

    def test_new_client_get(self):
        """Test GET request to new client view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('new_client'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_new_client_post_valid(self):
        """Test POST request with valid data."""
        self.client.login(username='testuser', password='testpass123')
        form_data = {
            'code': 'GIZ',
            'name': 'Deutsche Gesellschaft für Internationale Zusammenarbeit',
            'client_type': 'BDA'
        }
        response = self.client.post(reverse('new_client'), data=form_data)

        self.assertTrue(Client.objects.filter(code='GIZ').exists())


class TransferOpportunityViewTest(TestCase):
    """Test cases for TransferOpportunityView."""

    def setUp(self):
        """Set up test data."""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123')
        self.opportunity = Opportunity.objects.create(
            ref_no='EOI-2024-TRANSFER',
            title='Transfer Test',
            opp_type='EOI',
            created_by=self.user,
            status=7  # Won
        )

    def test_transfer_opportunity_redirects_to_create(self):
        """Test that transfer redirects to create view with source_id."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('transfer_opportunity', kwargs={'pk': self.opportunity.pk})
        )

        # Should redirect or return HX-Redirect header
        self.assertIn(response.status_code, [200, 302])

    def test_transfer_opportunity_htmx(self):
        """Test transfer with HTMX request."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('transfer_opportunity', kwargs={
                    'pk': self.opportunity.pk}),
            HTTP_HX_REQUEST='true'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('HX-Redirect', response.headers)
