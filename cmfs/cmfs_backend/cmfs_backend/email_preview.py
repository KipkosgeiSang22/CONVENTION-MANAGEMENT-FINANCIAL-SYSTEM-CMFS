"""
FILE: cmfs/cmfs_backend/cmfs_backend/email_preview.py
ACTION: CREATE (Phase 7)

DEBUG-only endpoint for eyeballing what each Resend template renders,
without a live Resend key or a real delegate/payment/convention row in
the database. Always 404s when DEBUG=False, regardless of auth.
"""
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

_CTX = {
    'full_name': 'Jane Wanjiru',
    'role_display': 'County Head',
    'setup_url': 'https://example.com/auth/setup?token=sample-token',
    'reset_url': 'https://example.com/auth/reset-password?token=sample-token',
    'delegate_id': 'NBI-STU-2026-0001',
    'category': 'Student',
    'county': 'Nairobi',
    'convention_name': 'KSCF National Convention 2026',
    'total_paid': '5,000.00',
    'balance': '0.00',
    'reason': 'Insufficient funds in M-Pesa account.',
    'retry_url': 'https://example.com/register/status/123?amount=5000',
}


def _invitation(ctx):
    return f"""
    <h2>Welcome to KSCF Convention System</h2>
    <p>Hello {ctx['full_name']},</p>
    <p>You have been assigned the role of <strong>{ctx['role_display']}</strong>.</p>
    <p>Click the link below to set up your password and authenticator app.
       This link expires in <strong>48 hours</strong>.</p>
    <p><a href="{ctx['setup_url']}">Set up my account</a></p>
    <p>Do not share this link with anyone.</p>
    """


def _password_reset(ctx):
    return f"""
    <h2>Password Reset</h2>
    <p>Hello {ctx['full_name']},</p>
    <p>A password reset was requested for your account.
       Click below to reset your password and re-configure your authenticator.
       This link expires in <strong>1 hour</strong>.</p>
    <p><a href="{ctx['reset_url']}">Reset my password</a></p>
    """


def _confirmation(ctx):
    return f"""
    <h2>You're registered!</h2>
    <p>Hello {ctx['full_name']},</p>
    <p>Your registration for <strong>{ctx['convention_name']}</strong> is confirmed.</p>
    <p>Delegate ID: <strong>{ctx['delegate_id']}</strong></p>
    <p>Category: {ctx['category']}</p>
    <p>County: {ctx['county']}</p>
    <p>Fee paid in full: <strong>KES {ctx['total_paid']}</strong></p>
    <p>Your QR code is attached — please bring it (printed or on your phone) to the gate.</p>
    """


def _payment_failure(ctx):
    return f"""
    <h2>Payment Not Completed</h2>
    <p>Hello {ctx['full_name']},</p>
    <p>Your M-Pesa payment for the convention registration did not go through.</p>
    <p>Reason: {ctx['reason']}</p>
    <p><a href="{ctx['retry_url']}">Click here to try again</a></p>
    """


def _payment_reminder(ctx):
    return f"""
    <h2>Payment Reminder</h2>
    <p>Hello {ctx['full_name']},</p>
    <p>This is a reminder that you have an outstanding balance of
       <strong>KES 2,500.00</strong> for <strong>{ctx['convention_name']}</strong>.</p>
    <p>Please settle this with your County Budget Creator, or via M-Pesa, before the convention.</p>
    """


TEMPLATES = {
    'invitation': _invitation,
    'password-reset': _password_reset,
    'confirmation': _confirmation,
    'payment-failure': _payment_failure,
    'payment-reminder': _payment_reminder,
}


class EmailPreviewView(APIView):
    """
    GET /api/email-preview/              — lists available template names
    GET /api/email-preview/<name>/       — renders that one template as raw HTML
    """
    permission_classes = []

    def get(self, request, template_name=None):
        if not settings.DEBUG:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not template_name:
            return Response({'templates': list(TEMPLATES.keys())})

        renderer = TEMPLATES.get(template_name)
        if not renderer:
            return Response({'error': 'Unknown template.', 'code': 'not_found'}, status=404)

        return HttpResponse(renderer(_CTX))
