"""
FILE: cmfs/cmfs_backend/cmfs_backend/utils/task_retry.py
ACTION: CREATE (Phase 7)

Shared retry wrapper for every Django Q2 task that talks to an external
service (Resend, in this phase). Django Q2 itself doesn't expose a clean
per-task "attempt number" hook, so retries are done in-process: call the
target function up to `max_attempts` times, and if every attempt fails,
write one audit log row so the failure is visible without crashing the
Q2 worker.

The action name is deliberately the single constant 'email_task_failed'
for every caller (including delegates.qr.generate_qr_code, which isn't
technically an email) to match the Phase 7 gate test contract: "email
task fails 3 times -> logged to audit_logs as email_task_failed".
"""
import logging

from auth_app.audit import log as audit_log

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
FAILURE_AUDIT_ACTION = 'email_task_failed'


def run_with_retries(send_fn, *args, task_name: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS, **kwargs) -> bool:
    """
    Calls send_fn(*args, **kwargs) up to `max_attempts` times.

    send_fn must return a truthy value on success; a falsy return value
    or a raised exception both count as a failed attempt. Returns True
    as soon as one attempt succeeds, or False once every attempt is
    exhausted (in which case a single 'email_task_failed' audit row is
    written, never raised, so a bad send never crashes the cluster).
    """
    last_error = ''
    for attempt in range(1, max_attempts + 1):
        try:
            result = send_fn(*args, **kwargs)
            if result:
                if attempt > 1:
                    logger.info(f'{task_name}: succeeded on attempt {attempt}/{max_attempts}')
                return True
            last_error = 'task returned a falsy result'
        except Exception as e:
            last_error = str(e)
            logger.warning(f'{task_name}: attempt {attempt}/{max_attempts} failed: {e}')

    logger.error(f'{task_name}: all {max_attempts} attempts failed — {last_error}')
    audit_log(
        action=FAILURE_AUDIT_ACTION,
        detail=f'{task_name} failed after {max_attempts} attempts: {last_error} (args={args!r})',
    )
    return False
