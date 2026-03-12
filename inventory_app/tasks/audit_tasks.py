# tasks/audit_tasks.py
"""
Tarea Celery para escritura asíncrona de registros de auditoría.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    ignore_result=True,
)
def log_audit_action(
    self,
    user_id,
    user_email,
    action,
    model_name,
    object_id,
    object_repr,
    changes,
    ip_address,
    user_agent,
):
    """
    Escribe un AuditLog de forma asíncrona, desacoplado de la transacción principal.
    Se encola vía transaction.on_commit() para garantizar que solo se ejecuta
    si la transacción exterior confirma (evita registros huérfanos en rollbacks).

    Args se pasan como tipos primitivos (serializable por Celery).
    """
    try:
        from inventory_app.models.audit_log import AuditLog
        from inventory_app.models.user import User

        user = None
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                pass

        log = AuditLog(
            user=user,
            user_email=user_email or 'anonymous',
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr or '',
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent or '',
        )
        log.save()
    except Exception as exc:
        logger.error(f"Error al guardar AuditLog async (model={model_name}, action={action}): {exc}")
        raise self.retry(exc=exc)
