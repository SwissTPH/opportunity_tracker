import datetime
from django.forms.widgets import Select
from typing import Any, Mapping
from django import forms
from tracker.workflows.service import get_required_fields, get_cumulative_required_fields
from tracker.workflows.registry import get_active_workflow
from tracker.workflows.schema import get_status_choices
from django.core.files.base import File
from django.db.models.base import Model
from django.forms.utils import ErrorList
from django.urls import reverse, reverse_lazy
from .models import Client, Country, FundingAgency, GoReason, Institute, Opportunity, OpportunityGoReason, OpportunityNoGoReason
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

User = get_user_model()


class FundingAgencyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.display_label


class ClientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.display_label


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput())
    next = forms.CharField(widget=forms.HiddenInput(), required=False)


class OpportunityForm(forms.ModelForm):
    funding_agency = FundingAgencyChoiceField(
        queryset=FundingAgency.objects.all(), required=False)
    client = ClientChoiceField(
        queryset=Client.objects.all(), required=False)

    class Meta:
        model = Opportunity
        fields = ['ref_no', 'title', 'funding_agency', 'client', 'opp_type', 'countries',
                  'due_date', 'clarification_date', 'intent_bid_date',  'duration_months', 'notes', 'status', 'currency', 'proposal_amount', 'is_noncompetitive']

        widgets = {
            'ref_no': forms.TextInput(attrs={'placeholder': 'Enter reference number'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'clarification_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'intent_bid_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'files': forms.ClearableFileInput(),
            'is_noncompetitive': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'duration_months': forms.TextInput(attrs={'placeholder': 'Enter duration in months'}),
            'proposal_amount': forms.TextInput(attrs={'placeholder': 'Enter proposal amount'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Enter additional notes'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['funding_agency'].widget.attrs.update({
            'data-url': reverse_lazy('new_funding_agency'),
            'data-entity': 'funding_agency',
        })

        self.fields['client'].widget.attrs.update({
            'data-url': reverse_lazy('new_client'),
            'data-entity': 'client',
        })

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()

        currency = cleaned_data.get("currency")
        proposal_amount = cleaned_data.get("proposal_amount")
        if (proposal_amount) and not currency:
            raise forms.ValidationError({
                'currency': 'Please select a currency.'
            })

        return cleaned_data

    status = forms.IntegerField(initial=1, widget=forms.HiddenInput())
    title = forms.CharField(
        required=True,
        error_messages={"required": "Title is required"},
        widget=forms.TextInput(attrs={'placeholder': 'Enter title'})
    )


class UpdateOpportunityForm(forms.ModelForm):
    funding_agency = FundingAgencyChoiceField(
        queryset=FundingAgency.objects.all(), required=False)
    client = ClientChoiceField(
        queryset=Client.objects.all(), required=False)

    partners = forms.ModelMultipleChoiceField(
        queryset=Institute.objects.all(), required=False, label="Partners")

    class Meta:
        model = Opportunity
        fields = ['ref_no', 'title', 'funding_agency', 'client', 'opp_type', 'countries',
                  'due_date', 'clarification_date', 'intent_bid_date', 'duration_months', 'notes', 'status', 'currency', 'proposal_amount',
                  'lead_unit', 'proposal_lead', 'submission_date', 'lead_institute', 'partners', 'submission_validity', 'result_note', 'is_noncompetitive',
                  'project_start_date', 'project_end_date']
        # Note: result_date is intentionally excluded - it's only managed via UpdateStatusForm

        widgets = {
            'ref_no': forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Enter reference number'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'clarification_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'intent_bid_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'submission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'project_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'project_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'files': forms.ClearableFileInput(),
            'is_noncompetitive': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'duration_months': forms.TextInput(attrs={'placeholder': 'Enter duration in months'}),
            'proposal_amount': forms.TextInput(attrs={'placeholder': 'Enter proposal amount'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Enter additional notes'}),
            'submission_validity': forms.NumberInput(attrs={'placeholder': 'Enter validity days'})
        }

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()

        status = int(cleaned_data.get("status", 0))

        # Drive required-field validation from workflow config, not hardcoded numbers.
        # Only validate fields that are actually included in this form.
        # (result_date is intentionally excluded — it lives in UpdateStatusForm only.)
        for field_name in get_cumulative_required_fields(status):
            if field_name not in self.fields:
                continue
            # Accept the value from POST data OR from the already-persisted instance.
            # This prevents false validation failures when a status-only modal submits
            # only a subset of fields that were already collected in earlier transitions.
            value = cleaned_data.get(field_name) or (
                getattr(self.instance, field_name,
                        None) if self.instance else None
            )
            if not value:
                label = self.fields[field_name].label or field_name.replace(
                    "_", " ").title()
                self.add_error(field_name, f"{label} is required")

        currency = cleaned_data.get("currency")
        proposal_amount = cleaned_data.get("proposal_amount")
        if (proposal_amount) and not currency:
            raise forms.ValidationError({
                'currency': 'Please select a currency.'
            })

        return cleaned_data

    title = forms.CharField(required=True, error_messages={
                            "required": "Title is required"}, widget=forms.TextInput(attrs={'placeholder': 'Enter title'}))

    def __init__(self, *args, **kwargs):
        from django.urls import reverse
        is_subscribed = kwargs.pop("is_subscribed", False)
        super().__init__(*args, **kwargs)

        self.fields['proposal_lead'].queryset = User.objects.all()
        self.fields['proposal_lead'].label_from_instance = lambda obj: f"{obj.first_name} {
            obj.last_name}" if obj.first_name and obj.last_name else obj.username

        self.fields["is_subscribed"].initial = is_subscribed
        if self.instance.pk:
            toggle_url = reverse('notification:toggle_subscription', kwargs={
                                 'opportunity_id': self.instance.pk})
            self.fields["is_subscribed"].widget.attrs.update({
                'hx-post': toggle_url,
                'hx-trigger': 'change',
                'hx-target': 'this',
                'hx-swap': 'none',
                'data-bs-toast-target': '#successToast',
            })

    status = forms.IntegerField(initial=1, widget=forms.HiddenInput())
    is_subscribed = forms.BooleanField(
        required=False, label="Subscribe to this Opportunity",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
        }))


class UpdateStatusForm(forms.ModelForm):
    result_date = forms.DateField(label="Result Date", required=False,
                                  widget=forms.DateInput(
                                      attrs={'class': 'form-control', 'type': 'date', 'max': datetime.date.today().isoformat(), 'placeholder': 'dd/mm/yyyy'})
                                  )
    project_start_date = forms.DateField(required=False,
                                         widget=forms.DateInput(
                                             attrs={
                                                 'class': 'form-control', 'type': 'date', 'placeholder': 'dd/mm/yyyy'}
                                         ))
    project_end_date = forms.DateField(required=False,
                                       widget=forms.DateInput(
                                           attrs={
                                               'class': 'form-control', 'type': 'date', 'placeholder': 'dd/mm/yyyy'}
                                       ))

    status = forms.ChoiceField(
        widget=forms.RadioSelect, label="status", choices=(), required=True, error_messages={'required': 'Select at least one option'})
    go_reasons_other_id = forms.UUIDField(
        required=False, widget=forms.HiddenInput())
    go_reasons_other_text = forms.CharField(required=False, label="Other reason",
                                            widget=forms.TextInput(attrs={'placeholder': 'Specify other reason'}))
    nogo_reasons_other_id = forms.UUIDField(
        required=False, widget=forms.HiddenInput())
    nogo_reasons_other_text = forms.CharField(required=False, label="Other reason",
                                              widget=forms.TextInput(attrs={'placeholder': 'Specify other reason'}))

    class Meta:
        model = Opportunity
        fields = ['status', 'lead_unit', 'proposal_lead',
                  'result_note', 'result_date', 'project_start_date', 'project_end_date', 'go_reasons', 'nogo_reasons']

        widgets = {
            'result_note': forms.TextInput(attrs={'placeholder': 'Enter notes'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Derive choices from the active workflow via the Opportunity instance.
        if self.instance and self.instance.pk:
            workflow_choices = self.instance.get_valid_status_choices()
        else:
            workflow_choices = get_status_choices(get_active_workflow())
        self.fields['status'].choices = [
            choice for choice in workflow_choices if choice[0] != 1
        ]
        self.fields['proposal_lead'].queryset = User.objects.all()
        self.fields['proposal_lead'].label_from_instance = lambda obj: f"{obj.first_name} {
            obj.last_name}" if obj.first_name and obj.last_name else obj.username
        if self.instance and self.instance.pk:
            submission_date = self.instance.submission_date
            if submission_date:
                self.fields['result_date'].widget.attrs['min'] = submission_date.isoformat(
                )

            other_entry = OpportunityGoReason.objects.filter(
                opportunity=self.instance,
                reason__reason__iexact='other'
            ).first()
            if other_entry:
                self.fields['go_reasons_other_text'].initial = other_entry.other_reason_description
                self.fields['go_reasons_other_id'].initial = str(
                    other_entry.reason_id)

            nogo_other_entry = OpportunityNoGoReason.objects.filter(
                opportunity=self.instance,
                reason__reason__iexact='other'
            ).first()
            if nogo_other_entry:
                self.fields['nogo_reasons_other_text'].initial = nogo_other_entry.other_reason_description
                self.fields['nogo_reasons_other_id'].initial = str(
                    nogo_other_entry.reason_id)

    def clean(self):
        cleaned_data = super().clean()
        status = int(cleaned_data.get("status", 0))

        # Drive required-field validation from workflow config, not hardcoded numbers.
        for field_name in get_required_fields(status):
            if not cleaned_data.get(field_name):
                if field_name in self.fields:
                    label = self.fields[field_name].label or field_name.replace(
                        "_", " ").title()
                else:
                    label = field_name.replace("_", " ").title()
                self.add_error(field_name, f"{label} is required")

        # Conditional validation for Go/No-Go
        GO_STATUS = 2
        NOGO_STATUS = 3

        selected_go_reasons = cleaned_data.get('go_reasons') or []
        selected_nogo_reasons = cleaned_data.get('nogo_reasons') or []

        if status == GO_STATUS and not selected_go_reasons:
            self.add_error('go_reasons', "Select at least one reason")

        if status == NOGO_STATUS and not selected_nogo_reasons:
            self.add_error('nogo_reasons', "Select at least one reason")

        other_id = cleaned_data.get('go_reasons_other_id')
        other_text = cleaned_data.get('go_reasons_other_text')

        if other_id:
            if not any(str(reason.id) == str(other_id) for reason in selected_go_reasons):
                cleaned_data['go_reasons_other_id'] = None
                cleaned_data['go_reasons_other_text'] = ''
            elif not other_text:
                self.add_error('go_reasons_other_text',
                               'This field is required when Other is selected.')
        else:
            cleaned_data['go_reasons_other_text'] = ''

        nogo_other_id = cleaned_data.get('nogo_reasons_other_id')
        nogo_other_text = cleaned_data.get('nogo_reasons_other_text')

        if nogo_other_id:
            if not any(str(reason.id) == str(nogo_other_id) for reason in selected_nogo_reasons):
                cleaned_data['nogo_reasons_other_id'] = None
                cleaned_data['nogo_reasons_other_text'] = ''
            elif not nogo_other_text:
                self.add_error('nogo_reasons_other_text',
                               'This field is required when Other is selected.')
        else:
            cleaned_data['nogo_reasons_other_text'] = ''

        return cleaned_data


class SubmitProposalForm(forms.ModelForm):
    submission_date = forms.DateField(required=True,
                                      error_messages={
                                          'required': 'Please provide a submission date'},
                                      widget=forms.DateInput(
                                          attrs={'class': 'form-control', 'type': 'date'})
                                      )
    lead_institute = forms.ModelChoiceField(
        queryset=Institute.objects.all(), required=True, label="Lead Organization", error_messages={'required': 'Select a Lead Organization'})

    partners = forms.ModelMultipleChoiceField(
        queryset=Institute.objects.all(), required=False, label="Partners")

    class Meta:
        model = Opportunity
        fields = ['status', 'lead_institute', 'partners',
                  'submission_date', 'submission_validity']
        widgets = {
            'submission_validity': forms.NumberInput(attrs={'placeholder': 'Enter validity days'})
        }


class OpportunityDetailForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        exclude = ['updated_at', 'updated_by']


class OpportunityDetailAnonymousForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        exclude = ['status', 'updated_at', 'updated_by']


class OpportunitySearchForm(forms.Form):
    ref_no = forms.CharField(
        required=False,
        label='Ref#',
        widget=forms.TextInput(attrs={'placeholder': 'Enter reference number'})
    )
    title = forms.CharField(required=False, label='Title', widget=forms.TextInput(
        attrs={'placeholder': 'Enter title'}))

    funding_agency = FundingAgencyChoiceField(
        queryset=FundingAgency.objects.all(), required=False, label="Funding Agency")
    client = ClientChoiceField(
        queryset=Client.objects.all(), required=False, label='Client')
    status = forms.ChoiceField(
        choices=(), required=False, label="Status")
    opp_type = forms.ChoiceField(
        choices=[('', '')] + Opportunity.OPP_TYPE, required=False, label="Type")
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(), required=False, label="Country")
    is_noncompetitive = forms.ChoiceField(
        choices=[('', 'Both'), (True, 'Non-competitive'),
                 (False, 'Competitive')],
        required=False, label="Competition Type")
    is_subscribed = forms.BooleanField(
        required=False, label="My Subscribed Opportunities",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
        }))

    def __init__(self, *args, **kwargs):
        from django.urls import reverse
        super().__init__(*args, **kwargs)

        # Use a bare Opportunity instance to delegate to the active workflow.
        self.fields['status'].choices = [
            ('', '')] + Opportunity().get_valid_status_choices()

        # Set the htmx attributes
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'hx-get':  reverse('opportunities'),
                'hx-target': '#opportunity-container',
                'hx-trigger': 'change' if isinstance(self.fields[field_name].widget, forms.Select) or isinstance(self.fields[field_name].widget, forms.CheckboxInput) else 'keyup changed delay:500ms',
            })


class FundingAgencyForm(forms.ModelForm):
    class Meta:
        model = FundingAgency
        fields = ["code", "name"]

        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Enter code'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter name'})
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["code", "name", "client_type"]

        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'Enter code'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter name'})
        }
