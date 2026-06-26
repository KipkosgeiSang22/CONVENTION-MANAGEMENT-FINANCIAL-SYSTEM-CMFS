"""
Helpers for writing append-only audit log entries.
"""
from reports.models import AuditLog


def log(user=None, action: str = '', detail: str = '', ip: str = ''):
    """
    Write one audit log row.  Never raises — a logging failure must not
    break the primary request.
    """
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            detail=detail,
            ip_address=ip,
        )
    except Exception:
        pass