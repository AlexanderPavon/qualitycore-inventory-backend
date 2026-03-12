# inventory_app/signals.py
"""
Signals de Django para registrar automáticamente cambios en AuditLog.
Usa ContextVar del AuditMiddleware para obtener el request (user, IP).
El registro se encola en Celery vía transaction.on_commit() para desacoplar
la auditoría de la transacción principal y no añadir latencia al hot path.
"""
import logging
from functools import lru_cache
from django.db import transaction
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

from inventory_app.models.product import Product
from inventory_app.models.customer import Customer
from inventory_app.models.supplier import Supplier
from inventory_app.models.user import User
from inventory_app.models.category import Category
from inventory_app.models.sale import Sale
from inventory_app.models.purchase import Purchase
from inventory_app.models.movement import Movement
from inventory_app.middleware import get_current_request

logger = logging.getLogger(__name__)

# Modelos a auditar y campos sensibles a excluir
SENSITIVE_FIELDS = {'password', 'last_login'}

# Campos internos que no aportan valor en el audit log.
# 'stock_in_movement' es específico del modelo Movement: se excluye del diff de
# actualizaciones porque ya es capturado explícitamente en los logs manuales de
# MovementService (con context de stock_before/stock_after). Si se renombra ese
# campo en Movement, actualizar este set.
SKIP_FIELDS = {'id', 'created_at', 'updated_at', 'stock_in_movement'}


def _get_field_value(instance, field_name):
    """Obtiene el valor de un campo de forma segura para JSON."""
    value = getattr(instance, field_name, None)
    if value is None:
        return None
    # Convertir tipos no serializables a string
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'pk'):
        return value.pk
    return value


def _get_changes(old_instance, new_instance, model):
    """Compara dos instancias y retorna los campos que cambiaron."""
    changes = {}
    for field in model._meta.concrete_fields:
        name = field.name
        if name in SENSITIVE_FIELDS or name in SKIP_FIELDS:
            continue
        old_val = _get_field_value(old_instance, name)
        new_val = _get_field_value(new_instance, name)
        if old_val != new_val:
            changes[name] = {'before': old_val, 'after': new_val}
    return changes


def _log(action, instance, changes=None):
    """
    Encola un AuditLog en Celery vía transaction.on_commit().
    El callback solo se ejecuta si la transacción exterior confirma,
    garantizando que no se generan registros huérfanos en rollbacks.
    Todos los datos se extraen del objeto antes del on_commit (el estado puede cambiar).
    """
    request = get_current_request()

    # Extraer datos serializables AHORA (el objeto puede mutar o ser borrado antes del commit)
    user = None
    user_email = 'anonymous'
    ip_address = None
    user_agent = ''
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        user_email = user.email
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    user_id = user.id if user else None
    object_id = instance.pk
    object_repr = str(instance)[:200]
    model_name = instance.__class__.__name__

    def enqueue():
        try:
            from inventory_app.tasks import log_audit_action
            log_audit_action.delay(
                user_id=user_id,
                user_email=user_email,
                action=action,
                model_name=model_name,
                object_id=object_id,
                object_repr=object_repr,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Error al encolar audit log ({model_name} {action}): {e}")

    transaction.on_commit(enqueue)


# --- pre_save: capturar estado anterior para detectar cambios ---

AUDITED_MODELS = [Product, Customer, Supplier, User, Category, Sale, Purchase, Movement]


@lru_cache(maxsize=None)
def _audit_fields_for(model_class) -> list:
    """Retorna los nombres de campos auditables para un modelo dado.
    Resultado cacheado por clase — se calcula solo la primera vez."""
    return [
        f.name for f in model_class._meta.concrete_fields
        if f.name not in SENSITIVE_FIELDS and f.name not in SKIP_FIELDS
    ]


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Guarda el estado anterior del objeto antes de guardarlo.

    Usa .only() con los campos relevantes para minimizar la query.
    La lista de campos se cachea por clase (lru_cache) para no recomputarla
    en cada save.
    """
    if sender not in AUDITED_MODELS:
        return

    if instance.pk:
        try:
            instance._audit_old = sender.objects.only(
                *_audit_fields_for(sender)
            ).get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._audit_old = None
    else:
        instance._audit_old = None


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Registra creación o actualización en AuditLog."""
    if sender not in AUDITED_MODELS:
        return

    if created:
        # Si el servicio marcó _skip_audit=True, él mismo llamará AuditLog.log_action
        # con datos más ricos (stock_after, original_movement_id, etc.).
        if getattr(instance, '_skip_audit', False):
            return
        _log('create', instance)
    else:
        old = getattr(instance, '_audit_old', None)
        if old:
            changes = _get_changes(old, instance, sender)
            if changes:
                _log('update', instance, changes=changes)


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    """Registra eliminación en AuditLog."""
    if sender not in AUDITED_MODELS:
        return

    _log('delete', instance)
