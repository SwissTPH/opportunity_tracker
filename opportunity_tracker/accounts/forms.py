from django.contrib.auth.forms import PasswordResetForm, PasswordChangeForm
from django.template import loader
from django.utils.html import strip_tags
from django.conf import settings
from notification.helpers.email_helper import EmailNotificationChannel


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom form for changing user password.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label


class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form to send HTML emails
    """

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send an email to `to_email` using the notification module's EmailNotificationChannel.
        """
        subject = f"Password reset for {settings.APP_NAME}"

        context["APP_NAME"] = settings.APP_NAME

        # Use the provided html_email_template_name if it exists
        if html_email_template_name:
            html_content = loader.render_to_string(
                html_email_template_name, context)
        else:
            # Fallback to the email_template_name
            html_content = loader.render_to_string(
                email_template_name, context)

        # Create the email notification channel
        email_channel = EmailNotificationChannel()

        # Send the email using the notification module
        email_channel.send(
            recipients=[to_email],
            subject=subject,
            message=html_content
        )
