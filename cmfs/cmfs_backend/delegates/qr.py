"""
FILE: cmfs/cmfs_backend/delegates/qr.py
ACTION: CREATE (Phase 7)

QR code generation for confirmed delegates. Encodes the Delegate ID
only (e.g. "KER-STU-2026-0042") — nothing else — so the Gate Check-In
app (Phase 8) has a single unambiguous lookup key and no personal data
ever sits inside the QR image itself.
"""
import logging
from pathlib import Path

import qrcode
from django.conf import settings

from cmfs_backend.utils.task_retry import run_with_retries

logger = logging.getLogger(__name__)

QR_DIR_NAME = 'qr_codes'


def qr_absolute_path(delegate) -> Path:
    """Absolute filesystem path to a delegate's QR PNG (used by delegates.emails to attach it)."""
    return Path(settings.MEDIA_ROOT) / QR_DIR_NAME / f'{delegate.delegate_id}.png'


def _generate_qr_code_once(delegate_id: int) -> bool:
    """
    `delegate_id` is the Delegate's numeric primary key (matches the
    argument on_payment_confirmed already receives) — not to be confused
    with the human-readable Delegate ID string encoded inside the image.
    """
    from .models import Delegate

    try:
        delegate = Delegate.objects.get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f'generate_qr_code: delegate {delegate_id} not found')
        return False

    if not delegate.delegate_id:
        logger.error(f'generate_qr_code: delegate pk={delegate_id} has no Delegate ID yet')
        return False

    qr_dir = Path(settings.MEDIA_ROOT) / QR_DIR_NAME
    qr_dir.mkdir(parents=True, exist_ok=True)
    filepath = qr_dir / f'{delegate.delegate_id}.png'

    try:
        img = qrcode.make(delegate.delegate_id)
        img.save(filepath)
    except Exception as e:
        logger.error(f'generate_qr_code: failed to generate/save QR for {delegate.delegate_id}: {e}')
        return False

    delegate.qr_code_path = f'{settings.MEDIA_URL}{QR_DIR_NAME}/{delegate.delegate_id}.png'
    delegate.save(update_fields=['qr_code_path'])

    logger.info(f'generate_qr_code: saved {filepath} for delegate {delegate.delegate_id}')
    return True


def generate_qr_code(delegate_id: int) -> bool:
    """
    Django Q2 task — retries the encode/save step up to 3 times before
    giving up and logging 'email_task_failed' to the audit log (see
    cmfs_backend.utils.task_retry for why that action name is shared
    across non-email tasks too).
    """
    return run_with_retries(_generate_qr_code_once, delegate_id, task_name='generate_qr_code')
