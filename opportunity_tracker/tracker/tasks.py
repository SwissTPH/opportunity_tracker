from urllib.parse import urljoin
from celery import shared_task
import datetime
import zoneinfo

from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from notification.models import NotificationSubscription
from notification.tasks import execute_channel_send

from .models import Opportunity


@shared_task
def send_weekly_summary(channel: str, days: int = 7):
    # Convert to local timezone for display
    local_time = timezone.now().astimezone(zoneinfo.ZoneInfo(settings.TIME_ZONE))
    print(
        f"📬 Sending a weekly summary for the channel {channel} at {local_time}")
    date_from = timezone.now() - datetime.timedelta(days=days)
    opportunities = Opportunity.objects.filter(
        created_at__gte=date_from, status=1).order_by('-created_at')

    if not opportunities.exists():
        return "No new opportunities to send."

    # Get all the active subscriptions
    subscriptions = NotificationSubscription.objects.filter(
        channel__name=channel, is_active=True)
    subscription_ids = list(subscriptions.values_list('id', flat=True))

    context = {
        'opportunities': opportunities,
        'date_from': date_from,
        'date_to': timezone.now(),
        'site_url': settings.SITE_URL,
        'APP_NAME': settings.APP_NAME
    }
    email_message = render_to_string(
        'tracker/emails/weekly_summary.html', context)

    short_message = f"{opportunities.count()} new opportunities created this week."

    execute_channel_send.delay(subscription_ids, NotificationSubscription.__name__, subject="Your Weekly Summary",
                               email_message=email_message, short_message=short_message)

    return f"Weekly summary sent to {len(subscription_ids)} subscribers for channel '{channel}'."
