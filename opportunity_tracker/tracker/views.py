import json
import os
import re
import zipfile
from typing import Any
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.utils.decorators import method_decorator
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)
from django_htmx.http import HttpResponseClientRefresh
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from notification.models import OpportunitySubscription
from tracker.services.fin_contribution_services import create_budget

from .forms import (OpportunityBudgetForm, OpportunityDetailForm, OpportunityDetailAnonymousForm, OpportunityForm,
                    OpportunitySearchForm, SubmitProposalForm,
                    UpdateOpportunityForm, UpdateStatusForm, FundingAgencyForm, ClientForm)
from .models import BudgetTemplate, BudgetTemplateColumn, BudgetTemplateRow, Currency, Opportunity, OpportunityBudget, OpportunityBudgetValue, OpportunityFile, OpportunityGoReason, OpportunityNoGoReason

from .serializers import OpportunitySerializer
from .workflows.registry import get_active_workflow
from .workflows.schema import get_status_slug_to_id
from .workflows.service import get_allowed_next_statuses, get_current_status_slug, get_current_status_group


User = get_user_model()


class OpportunityViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]  # Required JWT token
    permission_classes = [IsAuthenticated]  # Only allow authenticated users

    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer


class IndexView(View):
    template_name = "tracker/home.html"

    def get(self, request, *args, **kwargs):
        current_year = datetime.now().year
        context = {
            # From current year down to 2024
            "years": range(current_year, 2023, -1)
        }

        return render(request, self.template_name, context=context)


class OpportunityListView(ListView):
    model = Opportunity
    template_name = "tracker/list.html"
    paginate_by = 15
    form_class = OpportunitySearchForm

    def get_queryset(self):
        opportunities = Opportunity.objects.all().order_by("-created_at")
        form = OpportunitySearchForm(self.request.GET or None)

        # Apply filter
        if form.is_valid():
            ref_no = form.cleaned_data.get('ref_no', None)
            title = form.cleaned_data.get('title', None)
            funding_agency = form.cleaned_data.get('funding_agency', None)
            client = form.cleaned_data.get('client', None)
            status = form.cleaned_data.get('status', None)
            opp_type = form.cleaned_data.get('opp_type', None)
            country = form.cleaned_data.get('country', None)
            is_subscribed = form.cleaned_data.get('is_subscribed', None)
            is_noncompetitive = form.cleaned_data.get(
                'is_noncompetitive', None)

            if ref_no:
                opportunities = opportunities.filter(ref_no__icontains=ref_no)
            if title:
                opportunities = opportunities.filter(title__icontains=title)
            if funding_agency:
                opportunities = opportunities.filter(
                    funding_agency=funding_agency)
            if client:
                opportunities = opportunities.filter(client=client)
            if status:
                opportunities = opportunities.filter(status=status)
            if opp_type:
                opportunities = opportunities.filter(opp_type=opp_type)
            if country:
                opportunities = opportunities.filter(countries=country)
            if is_noncompetitive:
                opportunities = opportunities.filter(
                    is_noncompetitive=is_noncompetitive)
            if is_subscribed:
                subscriptions = OpportunitySubscription.objects.filter(
                    user=self.request.user,
                    is_active=True
                )

                opportunity_ids = subscriptions.values_list(
                    'opportunity', flat=True)

                opportunities = opportunities.filter(
                    id__in=opportunity_ids)

        return opportunities or Opportunity.objects.none()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class(self.request.GET or None)
        context['opportunity_count'] = context['page_obj'].paginator.count

        return context

    def get_template_names(self):
        if self.request.htmx:
            return "tracker/partials/opportunity_cards.html"
        else:
            return self.template_name


class FileDeleteView(DeleteView):
    model = OpportunityFile
    login_url = "accounts:login"

    def get_success_url(self) -> str:
        return reverse_lazy("opportunity", kwargs={"pk": self.object.opportunity.id})

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("", status=200)


class OpportunityCreateView(CreateView):
    model = Opportunity
    form_class = OpportunityForm
    template_name = "tracker/new.html"
    success_url = reverse_lazy("opportunities")
    login_url = "accounts:login"

    def get_initial(self):
        initial = super().get_initial()
        # Check if there's initial data from a transfer request (via query params)
        source_id = self.request.GET.get('source_id')
        if source_id:
            try:
                opportunity = Opportunity.objects.get(id=source_id)
                initial.update({
                    'title': opportunity.title,
                    'funding_agency': opportunity.funding_agency,
                    'client': opportunity.client,
                    'opp_type': 'RFP',  # Setting type to RFP
                    'countries': opportunity.countries.all(),
                    'status': 1,  # Set to "Entered" by default
                    'parent': opportunity,  # Set the parent relationship
                    'duration_months': opportunity.duration_months
                })
            except Opportunity.DoesNotExist:
                pass
            return initial

    def form_valid(self, form):
        from django.db import transaction

        form.instance.created_by = self.request.user

        # Check if this is a transfer operation and set parent if needed
        # Look for source_id in POST data first (from hidden input), then in GET parameters
        source_id = self.request.POST.get(
            'source_id') or self.request.GET.get('source_id')
        parent_opportunity = None

        if source_id:
            try:
                parent_opportunity = Opportunity.objects.get(id=source_id)
                form.instance.parent = parent_opportunity
            except Opportunity.DoesNotExist:
                pass

        # Use transaction to ensure atomicity of transfer operation
        with transaction.atomic():
            response = super().form_valid(form)

            # Create financial contributions
            budget_payload = form.cleaned_data.get("budget_payload")

            if budget_payload:
                create_budget(
                    self.object,
                    budget_payload
                )

            # Handle file upload
            files = self.request.FILES.getlist("files")
            for f in files:
                OpportunityFile.objects.create(opportunity=self.object, file=f)

            # If this is a transfer operation, update the parent opportunity status to "Transfer to RFP"
            # Only update status after the new RFP opportunity is successfully created
            if parent_opportunity and self.request.GET.get('is_transfer') == 'true':
                transfer_id = get_status_slug_to_id(
                    get_active_workflow()).get('transfer_to_rfp')
                if transfer_id is not None:
                    parent_opportunity.status = transfer_id
                    parent_opportunity.save()

        headers = {"HX-Trigger": "refresh_opp_list"}
        if self.request.htmx:
            return HttpResponse(status=204, headers=headers)
        else:
            return response

    def get_template_names(self):
        if self.request.htmx:
            return "tracker/new_modal.html"
        else:
            return self.template_name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add a flag to indicate if this is a transfer operation based on query param
        context['is_transfer'] = self.request.GET.get('is_transfer') == 'true'
        return context


class OpportunityUpdateView(UpdateView):
    model = Opportunity
    template_name = "tracker/update.html"
    form_class = UpdateOpportunityForm
    login_url = "accounts:login"
    # success_url = reverse_lazy("opportunities")

    def get_success_url(self):
        # Use reverse, not reverse_lazy here
        base_url = reverse("opportunities")
        query_params = self.request.GET.copy()
        query_params.pop("page", None)  # Optional: remove page param
        if query_params:
            return f"{base_url}?{query_params.urlencode()}"
        return base_url

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        if self.object:
            form.instance.ref_no = self.object.ref_no

        response = super().form_valid(form)

        # handle file upload
        # Handle file upload
        files = self.request.FILES.getlist("files")
        for f in files:
            OpportunityFile.objects.create(opportunity=self.object, file=f)

        if self.request.htmx:
            headers = {"HX-Redirect": str(self.get_success_url())}
            return HttpResponse(status=204, headers=headers)

        return response

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        subscription = OpportunitySubscription.objects.filter(
            user=self.request.user,
            opportunity=self.object,
            is_active=True
        ).first()

        if 'form' not in kwargs:
            context['form'] = UpdateOpportunityForm(
                instance=self.object, is_subscribed=subscription is not None)
        else:
            context['form'] = kwargs['form']  # Preserve form with errors

        context['update_status_form'] = UpdateStatusForm(instance=self.object)
        context['current_status_slug'] = get_current_status_slug(self.object)
        context['current_status_group'] = get_current_status_group(self.object)
        context['allowed_next_statuses'] = get_allowed_next_statuses(
            self.object)
        if not self.submit_proposal_form:
            context['submit_proposal_form'] = SubmitProposalForm(
                instance=self.object)
        else:
            context['submit_proposal_form'] = self.submit_proposal_form

        filters = self.request.GET.copy()
        filters.pop('page', None)  # Remove 'page' if present
        context['back_query'] = filters.urlencode()

        return context

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context, status=400)

    def get_template_names(self):
        if self.request.htmx:
            return "tracker/update.html"
        return super().get_template_names()

    def dispatch(self, request, *args, **kwargs):
        # Extract additional kwargs if provided
        self.submit_proposal_form = kwargs.pop(
            'submit_proposal_form', None)
        return super().dispatch(request, *args, **kwargs)


class OpportunityStatusUpdateView(UpdateView):
    print("Regular update....")
    model = Opportunity
    form_class = UpdateStatusForm
    template_name = "tracker/partials/update_status_modal.html"
    # success_url = reverse_lazy("opportunities")

    def get_success_url(self):
        # Use reverse, not reverse_lazy here
        base_url = reverse("opportunities")
        query_params = self.request.GET.copy()
        query_params.pop("page", None)  # Optional: remove page param
        if query_params:
            return f"{base_url}?{query_params.urlencode()}"
        return base_url

    def _save_go_reasons(self, opportunity, selected_reasons, other_reason_id, other_reason_text):
        OpportunityGoReason.objects.filter(opportunity=opportunity).delete()
        if not selected_reasons:
            return

        for reason in selected_reasons:
            if other_reason_id and str(reason.id) == str(other_reason_id):
                OpportunityGoReason.objects.create(
                    opportunity=opportunity,
                    reason=reason,
                    other_reason_description=other_reason_text
                )
            else:
                OpportunityGoReason.objects.create(
                    opportunity=opportunity,
                    reason=reason
                )

    def _save_nogo_reasons(self, opportunity, selected_reasons, other_reason_id, other_reason_text):
        OpportunityNoGoReason.objects.filter(opportunity=opportunity).delete()
        if not selected_reasons:
            return

        for reason in selected_reasons:
            if other_reason_id and str(reason.id) == str(other_reason_id):
                OpportunityNoGoReason.objects.create(
                    opportunity=opportunity,
                    reason=reason,
                    other_reason_description=other_reason_text
                )
            else:
                OpportunityNoGoReason.objects.create(
                    opportunity=opportunity,
                    reason=reason
                )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # hx-include="#opportunityForm" causes the parent form's hidden
        # status field (current DB status) to be appended to the POST data
        # after the modal radio button value.  Django QueryDict.get() returns
        # the *last* value, which would be the wrong one.  Take the first
        # occurrence instead — that is always the modal radio selection.
        post_data = request.POST
        if len(request.POST.getlist('status')) > 1:
            post_data = request.POST.copy()
            post_data.setlist('status', [request.POST.getlist('status')[0]])

        # Process both the status form and the main opportunity form
        status_form = UpdateStatusForm(post_data, instance=self.object)
        main_form = UpdateOpportunityForm(
            post_data, request.FILES, instance=self.object)

        # Validate both forms separately to ensure both are checked
        status_valid = status_form.is_valid()
        main_valid = main_form.is_valid()

        print(f"Status form valid: {status_valid}")
        print(f"Status form errors: {status_form.errors}")
        print(f"Main form valid: {main_valid}")
        print(f"Main form errors: {main_form.errors}")

        if status_valid and main_valid:
            # Save the original result_date before any modifications
            original_result_date = self.object.result_date

            # Update the main form fields first
            main_form.instance.updated_by = self.request.user

            # Override with status form fields (these take precedence)
            status_obj = status_form.save(commit=False)
            main_form.instance.status = status_obj.status
            main_form.instance.lead_unit = status_obj.lead_unit
            main_form.instance.proposal_lead = status_obj.proposal_lead
            main_form.instance.result_note = status_obj.result_note

            # Only update result_date if it's provided in the status form
            # Otherwise, preserve the original value
            if status_obj.result_date is not None:
                main_form.instance.result_date = status_obj.result_date
            else:
                main_form.instance.result_date = original_result_date

            # Save the combined data
            main_obj = main_form.save()

            status = main_form.instance.status

            if status == 2:
                # Save go_reasons through model data, including other_reason_description.
                self._save_go_reasons(
                    main_obj,
                    status_form.cleaned_data.get('go_reasons'),
                    status_form.cleaned_data.get('go_reasons_other_id'),
                    status_form.cleaned_data.get('go_reasons_other_text')
                )

                # Clear any No-go reasons
                self._save_nogo_reasons(main_obj, None, None, None)

            elif status == 3:
                # Save nogo_reasons through model data, including other_reason_description.
                self._save_nogo_reasons(
                    main_obj,
                    status_form.cleaned_data.get('nogo_reasons'),
                    status_form.cleaned_data.get('nogo_reasons_other_id'),
                    status_form.cleaned_data.get('nogo_reasons_other_text')
                )

                # Clear any existing go reasons
                self._save_go_reasons(main_obj, None, None, None)

            # Handle file uploads from the main form
            files = self.request.FILES.getlist("files")
            for f in files:
                OpportunityFile.objects.create(opportunity=main_obj, file=f)

            if self.request.htmx:
                headers = {"HX-Redirect": str(self.get_success_url())}
                return HttpResponse(status=204, headers=headers)

            return super().form_valid(status_form)
        else:
            return self.form_invalid(status_form)

    def form_valid(self, form):
        self.object = form.save()
        if self.request.htmx:
            # return HttpResponseClientRefresh()
            headers = {"HX-Redirect": str(self.get_success_url())}
            return HttpResponse(status=204, headers=headers)

        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.htmx:
            errors = form.errors.as_json()
            print(errors)

            # If there are errors in the main form, we need to render those too
            main_form_data = {k: v for k, v in self.request.POST.items()}
            main_form = UpdateOpportunityForm(
                main_form_data, instance=self.object)

            context = self.get_context_data(
                update_status_form=form,
                form=main_form)  # Pass both forms with errors

            headers = {"HX-Trigger": "form_invalid"}
            return self.render_to_response(context, headers=headers)

        return super().form_invalid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Use a fresh DB copy so bound form POST data does not mutate the
        # in-memory instance and accidentally change the available options.
        current_opportunity = Opportunity.objects.get(pk=self.object.pk)
        context['current_status_id'] = current_opportunity.status

        if 'update_status_form' in kwargs:
            context['update_status_form'] = kwargs["update_status_form"]
        else:
            context['update_status_form'] = UpdateStatusForm(
                instance=current_opportunity)

        context['filtered_status'] = get_allowed_next_statuses(
            current_opportunity)

        wf = get_active_workflow()
        slug_to_id = get_status_slug_to_id(wf)
        context['transfer_to_rfp_id'] = slug_to_id.get('transfer_to_rfp')
        context['go_status_id'] = slug_to_id.get('go')
        context['nogo_status_id'] = slug_to_id.get('no_go')
        context['won_status_id'] = slug_to_id.get('won')
        result_date_ids_list = [
            str(slug_to_id[s])
            for s, fields in wf.get('required_fields', {}).items()
            if 'result_date' in fields and s in slug_to_id
        ]
        context['result_date_status_ids'] = json.dumps(result_date_ids_list)
        context['result_date_status_ids_list'] = result_date_ids_list

        return context

    def get_template_names(self):
        if self.request.htmx:
            return "tracker/partials/update_status_modal.html"
        return super().get_template_names()


class OpportunitySubmitView(UpdateView):
    model = Opportunity
    form_class = SubmitProposalForm
    template_name = "tracker/partials/submit_proposal_modal.html"
    # success_url = reverse_lazy("opportunities")

    def get_success_url(self):
        # Use reverse, not reverse_lazy here
        base_url = reverse("opportunities")
        query_params = self.request.GET.copy()
        query_params.pop("page", None)  # Optional: remove page param
        if query_params:
            return f"{base_url}?{query_params.urlencode()}"
        return base_url

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Process both the proposal submit form and the main opportunity form
        proposal_form = self.get_form()
        main_form = UpdateOpportunityForm(
            request.POST, request.FILES, instance=self.object)

        if proposal_form.is_valid() and main_form.is_valid():
            # Update the main form fields first
            main_form.instance.updated_by = self.request.user
            main_obj = main_form.save()

            # Then update the proposal form fields
            proposal_obj = proposal_form.save(commit=False)
            # Set the fields that are specific to proposal submission
            main_obj.status = 5  # Set status to submitted (5)
            main_obj.lead_institute = proposal_obj.lead_institute
            main_obj.partners.set(proposal_obj.partners.all())
            main_obj.submission_date = proposal_obj.submission_date
            main_obj.save()

            # Handle file uploads from the main form
            files = self.request.FILES.getlist("files")
            for f in files:
                OpportunityFile.objects.create(opportunity=main_obj, file=f)

            if self.request.htmx:
                headers = {"HX-Redirect": str(self.get_success_url())}
                return HttpResponse(status=204, headers=headers)

            return self.form_valid(proposal_form)
        else:
            return self.form_invalid(proposal_form)

    def form_valid(self, form):
        self.object = form.save()
        if self.request.htmx:
            headers = {"HX-Redirect": str(self.get_success_url())}
            return HttpResponse(status=204, headers=headers)

        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if 'submit_proposal_form' in kwargs:
            context["submit_proposal_form"] = kwargs["submit_proposal_form"]
        else:
            context['submit_proposal_form'] = SubmitProposalForm(
                instance=self.object)

        return context

    def form_invalid(self, form):
        view = OpportunityUpdateView.as_view()
        return view(self.request, pk=self.object.id, submit_proposal_form=form)

    def get_template_names(self):
        if self.request.htmx:
            return "tracker/partials/submit_proposal_modal.html"
        return super().get_template_names()


class OpportunityDetailView(DetailView):
    model = Opportunity
    template_name = "tracker/detail_modal.html"
    context_object_name = "opportunity"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        opportunity = self.get_object()
        form = OpportunityDetailForm(instance=opportunity)
        context['form'] = form
        context['partner_names'] = [
            partner.name for partner in opportunity.partners.all()]

        context['files'] = opportunity.Files.all()

        # Get the decision reason go/no-go
        if opportunity.status == 2:
            context['reasons'] = opportunity.opportunitygoreason_set.select_related(
                'reason')

        elif opportunity.status == 3:
            context['reasons'] = opportunity.opportunitynogoreason_set.select_related(
                'reason')

        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Handle the AJAX call
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            opportunity = self.get_object()
            form = OpportunityDetailForm(instance=opportunity)
            files = opportunity.Files.all()
            html = render_to_string(
                "tracker/detail_modal.html", {"form": form, "files": files, })
            return JsonResponse({'html': html})

        return super().get(request, *args, **kwargs)


@method_decorator(login_not_required, name='dispatch')
class OpportunityDetailAnonymousView(DeleteView):
    model = Opportunity
    form_class = OpportunityDetailAnonymousForm
    template_name = "tracker/detail_anonymous.html"
    context_object_name = "opportunity"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        opportunity = self.get_object()
        form = OpportunityDetailAnonymousForm(instance=opportunity)
        context['form'] = form
        context['partner_names'] = [
            partner.name for partner in opportunity.partners.all()]

        context['files'] = opportunity.Files.all()

        # Get the decision reason go/no-go
        if opportunity.status == 2:
            context['reasons'] = opportunity.opportunitygoreason_set.select_related(
                'reason')

        elif opportunity.status == 3:
            context['reasons'] = opportunity.opportunitynogoreason_set.select_related(
                'reason')

        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Handle the AJAX call
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            opportunity = self.get_object()
            form = OpportunityDetailAnonymousForm(instance=opportunity)
            files = opportunity.Files.all()
            html = render_to_string(
                "tracker/detail_modal.html", {"form": form, "files": files, })
            return JsonResponse({'html': html})

        return super().get(request, *args, **kwargs)


class DownloadFolderView(View):
    def get(self, request, pk):

        # Get the opportunity
        opportunity = Opportunity.objects.filter(id=pk).first()

        if not opportunity:
            return HttpResponse("Opportunity not found", status=404)

        # Get all the files
        files = opportunity.Files.all()

        if not files.exists():
            return HttpResponse("No attachment found", status=404)

        # Create a zip file in memory
        ref_no = foldername = re.sub(r"[^a-zA-Z0-9]", "_", opportunity.ref_no)
        zip_filename = f"{ref_no}.zip"
        zip_path = os.path.join(settings.MEDIA_ROOT, "temp", zip_filename)

        # Ensure the temp folder exists
        os.makedirs(os.path.join(settings.MEDIA_ROOT, "temp"), exist_ok=True)

        with zipfile.ZipFile(zip_path, "w") as zip_file:
            for file in files:
                file_path = file.file.path
                # Relative path inside zip
                archname = os.path.relpath(
                    file_path, os.path.join(settings.MEDIA_ROOT, "opportunities", ref_no))
                zip_file.write(file_path, archname)

        # Serve the zip file
        with open(zip_path, "rb") as file:
            response = HttpResponse(
                file.read(), content_type="application/zip")
            response["Content-Disposition"] = f"attachment \
            filename = {
                zip_filename}"

        # Clean up the zip file
        os.remove(zip_path)

        return response


class NewFundingAgencyView(View):
    template_name = "tracker/new_funding_agency.html"
    form_class = FundingAgencyForm
    success_url = reverse_lazy("new_opportunity")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            agency = form.save()
            if request.htmx:
                return JsonResponse(
                    {
                        "id": agency.id,
                        "name": agency.name
                    },
                    status = 201
                )

        return render(request, self.template_name, {"form": form})


class NewClientView(View):
    template_name = "tracker/new_client.html"
    form_class = ClientForm
    success_url = reverse_lazy("new_opportunity")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            client = form.save()
            if request.htmx:
                return JsonResponse(
                    {
                        "id": client.id,
                        "name": client.name
                    },
                    status = 201
                )

        return render(request, self.template_name, {"form": form})


class TransferOpportunityView(View):
    def post(self, request, pk):
        opportunity = Opportunity.objects.get(id=pk)

        # Don't update status here - it will be updated in OpportunityCreateView.form_valid
        # only when the new RFP opportunity is successfully created

        # Use direct HttpResponseRedirect for more reliable redirection
        from django.http import HttpResponseRedirect
        redirect_url = f"{reverse('new_opportunity')}?source_id={opportunity.id}&is_transfer=true"

        print("Redirecting to:", redirect_url)

        if request.htmx:
            return HttpResponse(
                "",  # Empty response body
                status = 200,  # Use 200 instead of 204 for more reliable processing
                headers = {
                    "HX-Redirect": redirect_url
                }
            )
        else:
            # Fallback to standard redirect for non-HTMX requests
            return HttpResponseRedirect(redirect_url)


# Financial Contribution
class OpportunityBudgetView(View):
    model = BudgetTemplate
    form_class = OpportunityBudgetForm
    template_name = "tracker/partials/fin_contribution_modal.html"

    def get(self, request, *args, **kwargs):
        template = BudgetTemplate.objects.get(is_active=True)
        currency_id = request.GET.get('currency')
        opportunity_id = request.GET.get('opportunity_id')
        currency = Currency.objects.filter(pk=currency_id).first()

        print(currency_id)

        context = {
            'form': OpportunityBudgetForm(),
            'template': template,
            'columns': template.columns.all(),
            'rows': template.rows.all(),
            'currency': currency,
            'opportunity_id': opportunity_id
        }

        return render(request, self.template_name, context)


class OpportunityBudgetUpdateView(View):
    def post(self, request, *args, **kwargs):
        opportunity_id = request.POST.get("opportunity_id")
        budget_payload = request.POST.get("budget_payload")
        proposal_amount = request.POST.get("proposal_amount")

        # Validate the form
        form = OpportunityBudgetForm(request.POST)
        if not form.is_valid():
            return JsonResponse(
                {"errors": form.errors},
                status = 400
            )

        if budget_payload:
            opportunity = get_object_or_404(
                Opportunity,
                pk=opportunity_id
            )

            if hasattr(opportunity, "budget"):
                opportunity.budget.delete()

            create_budget(
                opportunity,
                budget_payload
            )

            opportunity.proposal_amount = proposal_amount
            opportunity.save(update_fields=["proposal_amount"])

            return HttpResponse(status=204)
