# inventory_app/signals.py
"""
Signals de Django para registrar automáticamente cambios en AuditLog.
Usa thread-local del AuditMiddleware para obtener el request (user, IP).
"""
import logging
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

from inventory_app.models.audit_log import AuditLog
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

# Campos internos que no aportan valor en el audit log
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
    """Crea un registro en AuditLog con info del request actual."""
    request = get_current_request()
    user = None
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user

    try:
        AuditLog.log_action(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            obj=instance,
            changes=changes,
            request=request,
        )
    except Exception as e:
        # Nunca bloquear la operación original por un fallo en auditoría
        logger.error(f"Error al crear audit log: {e}")


# --- pre_save: capturar estado anterior para detectar cambios ---

AUDITED_MODELS = [Product, Customer, Supplier, User, Category, Sale, Purchase, Movement]


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Guarda el estado anterior del objeto antes de guardarlo.

    Usa .only() con los campos relevantes para minimizar la query.
    Excluye campos que nunca se auditan (SENSITIVE_FIELDS + SKIP_FIELDS).
    """
    if sender not in AUDITED_MODELS:
        return

    if instance.pk:
        try:
            # Solo traer los campos que realmente se comparan (evita SELECT *)
            audit_fields = [
                f.name for f in sender._meta.concrete_fields
                if f.name not in SENSITIVE_FIELDS and f.name not in SKIP_FIELDS
            ]
            instance._audit_old = sender.objects.only(*audit_fields).get(pk=instance.pk)
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
