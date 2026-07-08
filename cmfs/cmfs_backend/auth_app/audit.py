"""
Helpers for writing append-only audit log entries.

FIX (Phase 7): the previous version called
AuditLog.objects.create(user=user, detail=detail, ...) but the model has
no `user` or `detail` fields (it has user_id / user_name / new_value) —
every call silently failed inside the try/except below, so no audit log
row has ever actually been written by any phase up to now. Phase 7's own
gate test ("email task fails 3 times -> logged to audit_logs as
email_task_failed") needs this to really persist, so it's fixed here
without changing the call signature every other app already relies on.
"""
from reports.models import AuditLog


def log(user=None, action: str = '', detail: str = '', ip: str = ''):
    """
    Write one audit log row. Never raises — a logging failure must not
    break the primary request.

    `user` may be a User instance, a raw user id, or None (system/
    background-task action, e.g. from a Django Q2 task with no request).
    `detail` has no dedicated free-text column on AuditLog, so it's
    stored inside `new_value` as {'detail': ...}.
    """
    try:
        if hasattr(user, 'id'):
            user_id = user.id
            user_name = getattr(user, 'full_name', '') or ''
        elif user is not None:
            user_id = user
            user_name = ''
        else:
            user_id = None
            user_name = ''

        AuditLog.objects.create(
            user_id=user_id,
            user_name=user_name,
            action=action,
            new_value={'detail': detail} if detail else None,
            ip_address=ip or None,
        )
    except Exception:
        pass
