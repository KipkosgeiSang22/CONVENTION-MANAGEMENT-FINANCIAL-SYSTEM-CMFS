"""
FILE: cmfs/cmfs_backend/auth_app/emails.py
ACTION: MODIFY (Phase 7)

Auth-related Resend emails. Each public function is a Django Q2 task
(queued with async_task, never called synchronously from a view) and
takes a user_id rather than a User instance so it stays trivially
serialisable across the task queue; it rebuilds the setup/reset URL
itself from the token already saved on the user row rather than having
the caller pass it in. Each one retries up to 3 times via
cmfs_backend.utils.task_retry before giving up and logging
"email_task_failed" to the audit log.
"""
import logging
import resend
from django.conf import settings

from cmfs_backend.utils.task_retry import run_with_retries

logger = logging.getLogger(__name__)

FROM_ADDRESS = getattr(settings, "RESEND_FROM_EMAIL", "noreply@kscf.or.ke")


def _send(to: str, subject: str, html: str) -> bool:
    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as exc:
        logger.error("Resend error sending to %s: %s", to, exc)
        return False


def _send_invitation_email_once(user_id: int) -> bool:
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"send_invitation_email: user {user_id} not found")
        return False

    if not user.setup_token:
        logger.error(f"send_invitation_email: user {user_id} has no setup_token")
        return False

    setup_url = f"{settings.FRONTEND_URL}/auth/setup?token={user.setup_token}"
    html = f"""
    <h2>Welcome to KSCF Convention System</h2>
    <p>Hello {user.full_name},</p>
    <p>You have been assigned the role of <strong>{user.get_role_display()}</strong>.</p>
    <p>Click the link below to set up your password and authenticator app.
       This link expires in <strong>48 hours</strong>.</p>
    <p><a href="{setup_url}">Set up my account</a></p>
    <p>Do not share this link with anyone.</p>
    """
    return _send(user.email, "Set up your KSCF Convention System account", html)


def send_invitation_email(user_id: int) -> bool:
    """
    Django Q2 task — queue with async_task('auth_app.emails.send_invitation_email', user.id).
    setup_url is also always returned directly by the invite API response
    (see auth_app.views.InviteUserView), independent of whether this
    email actually goes through.
    """
    return run_with_retries(_send_invitation_email_once, user_id, task_name="send_invitation_email")


def _send_password_reset_email_once(user_id: int) -> bool:
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"send_password_reset_email: user {user_id} not found")
        return False

    if not user.setup_token:
        logger.error(f"send_password_reset_email: user {user_id} has no setup_token")
        return False

    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={user.setup_token}"
    html = f"""
    <h2>Password Reset</h2>
    <p>Hello {user.full_name},</p>
    <p>A password reset was requested for your account.
       Click below to reset your password and re-configure your authenticator.
       This link expires in <strong>1 hour</strong>.</p>
    <p><a href="{reset_url}">Reset my password</a></p>
    <p>If you did not request this, ignore this email.</p>
    """
    return _send(user.email, "KSCF Convention System — Password Reset", html)


def send_password_reset_email(user_id: int) -> bool:
    """Django Q2 task — queue with async_task('auth_app.emails.send_password_reset_email', user.id)."""
    return run_with_retries(_send_password_reset_email_once, user_id, task_name="send_password_reset_email")
