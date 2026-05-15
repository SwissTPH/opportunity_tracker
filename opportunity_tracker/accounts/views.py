from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.views import PasswordResetView, PasswordChangeView, LoginView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomPasswordResetForm, CustomPasswordChangeForm


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Custom view for changing password"""
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        messages.success(
            self.request, "Your password has been changed successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that uses notification module to send emails"""
    form_class = CustomPasswordResetForm
