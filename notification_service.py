"""
notification_service.py
------------------------
Sends contract lifecycle notifications via email and Slack.
Handles expiry alerts, approval requests, and signature reminders
with configurable channels and priority levels.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    BOTH  = "both"


class Priority(Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


@dataclass
class Recipient:
    name: str
    email: str
    slack_user_id: Optional[str] = None


@dataclass
class Notification:
    subject: str
    body: str
    priority: Priority
    channel: NotificationChannel
    recipients: list[Recipient]
    sent_at: Optional[datetime] = None
    success: bool = False


# ── Email sender (stub — replace with SendGrid / SES in production) ───────────

def send_email(recipient: Recipient, subject: str, body: str) -> bool:
    """
    Send an email notification to a single recipient.
    Returns True on success, False on failure.

    In production: integrate with SendGrid, AWS SES, or SMTP.
    """
    if not recipient.email:
        log.warning("No email address for recipient '%s' — skipping", recipient.name)
        return False

    log.info("EMAIL → %s <%s> | Subject: %s", recipient.name, recipient.email, subject)
    # TODO: replace with real email client call
    return True


# ── Slack sender (stub — replace with Slack Web API in production) ────────────

def send_slack(recipient: Recipient, subject: str, body: str) -> bool:
    """
    Send a Slack DM to a single recipient via their Slack user ID.
    Returns True on success, False on failure.

    In production: use slack_sdk.WebClient.chat_postMessage().
    """
    if not recipient.slack_user_id:
        log.warning(
            "No Slack user ID for recipient '%s' — falling back to email",
            recipient.name,
        )
        return send_email(recipient, subject, body)

    log.info("SLACK → @%s (%s) | Subject: %s", recipient.name, recipient.slack_user_id, subject)
    # TODO: replace with real Slack SDK call
    return True


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(notification: Notification) -> Notification:
    """
    Send a Notification to all recipients via the configured channel.
    Updates notification.success and notification.sent_at in place.
    Returns the updated Notification.
    """
    results = []

    for recipient in notification.recipients:
        if notification.channel == NotificationChannel.EMAIL:
            ok = send_email(recipient, notification.subject, notification.body)

        elif notification.channel == NotificationChannel.SLACK:
            ok = send_slack(recipient, notification.subject, notification.body)

        else:  # BOTH
            email_ok = send_email(recipient, notification.subject, notification.body)
            slack_ok = send_slack(recipient, notification.subject, notification.body)
            ok = email_ok or slack_ok   # success if at least one channel worked

        results.append(ok)

    notification.success  = all(results)
    notification.sent_at  = datetime.now(timezone.utc)

    if not notification.success:
        log.error(
            "Notification '%s' failed for one or more recipients", notification.subject
        )

    return notification


# ── Pre-built notification factories ─────────────────────────────────────────

def expiry_alert(
    contract_id: str,
    days_remaining: int,
    recipients: list[Recipient],
    channel: NotificationChannel = NotificationChannel.BOTH,
) -> Notification:
    """Build an expiry alert notification for a contract nearing its end date."""
    priority = Priority.HIGH if days_remaining <= 7 else Priority.MEDIUM
    return Notification(
        subject=f"Contract {contract_id} expires in {days_remaining} day(s)",
        body=(
            f"Contract {contract_id} is due to expire in {days_remaining} day(s).\n"
            "Please review and initiate renewal if required."
        ),
        priority=priority,
        channel=channel,
        recipients=recipients,
    )


def approval_request(
    contract_id: str,
    approver: Recipient,
    requested_by: str,
    value: float,
    currency: str,
) -> Notification:
    """Build a high-value contract approval request notification."""
    return Notification(
        subject=f"Approval required: Contract {contract_id} ({currency} {value:,.2f})",
        body=(
            f"{requested_by} has submitted contract {contract_id} for approval.\n"
            f"Contract value: {currency} {value:,.2f}\n"
            "Please review and approve or reject within 48 hours."
        ),
        priority=Priority.HIGH,
        channel=NotificationChannel.BOTH,
        recipients=[approver],
    )


def signature_reminder(contract_id: str, recipients: list[Recipient]) -> Notification:
    """Build a signature reminder for an unsigned contract."""
    return Notification(
        subject=f"Signature required: Contract {contract_id}",
        body=(
            f"Contract {contract_id} is awaiting your signature.\n"
            "Please sign at your earliest convenience to make it enforceable."
        ),
        priority=Priority.MEDIUM,
        channel=NotificationChannel.EMAIL,
        recipients=recipients,
    )
