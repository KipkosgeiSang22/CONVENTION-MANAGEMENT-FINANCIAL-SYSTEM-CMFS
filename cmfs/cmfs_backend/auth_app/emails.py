"""
Thin wrappers around Resend for auth-related emails.
All sends are fire-and-forget — errors are logged, not re-raised.
"""
import logging
import resend
from django.conf import settings

logger = logging.getLogger(__name__)

FROM_ADDRESS = 'noreply@kscf.or.ke'


def _send(to: str, subject: str, html: str):
    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            'from': FROM_ADDRESS,
            'to': [to],
            'subject': subject,
            'html': html,
        })
    except Exception as exc:
        logger.error('Resend error sending to %s: %s', to, exc)


def send_invitation_email(user, setup_url: str):
    html = f"""
    <h2>Welcome to KSCF Convention System</h2>
    <p>Hello {user.full_name},</p>
    <p>You have been assigned the role of <strong>{user.get_role_display()}</strong>.</p>
    <p>Click the link below to set up your password and authenticator app.
       This link expires in <strong>48 hours</strong>.</p>
    <p><a href="{setup_url}">Set up my account</a></p>
    <p>Do not share this link with anyone.</p>
    """
    _send(user.email, 'Set up your KSCF Convention System account', html)


def send_password_reset_email(user, reset_url: str):
    html = f"""
    <h2>Password Reset</h2>
    <p>Hello {user.full_name},</p>
    <p>A password reset was requested for your account.
       Click below to reset your password and re-configure your authenticator.
       This link expires in <strong>1 hour</strong>.</p>
    <p><a href="{reset_url}">Reset my password</a></p>
    <p>If you did not request this, ignore this email.</p>
    """
    _send(user.email, 'KSCF Convention System — Password Reset', html)