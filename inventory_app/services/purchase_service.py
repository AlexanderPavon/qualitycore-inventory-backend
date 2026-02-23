# services/purchase_service.py
"""
Servicio para gestionar lógica de negocio de compras.
Hereda la lógica compartida de TransactionServiceBase.
"""

from django.core.exceptions import ValidationError

from inventory_app.models import Purchase, Supplier
from inventory_app.constants import MovementType
from inventory_app.services.transaction_base import TransactionServiceBase


class PurchaseService(TransactionServiceBase):

    @staticmethod
    def create_purchase(supplier_id, user_id, items):
        return PurchaseService.create(supplier_id, user_id, items)

    @classmethod
    def _validate_entity(cls, entity_id):
        try:
            return Supplier.objects.get(id=entity_id, deleted_at__isnull=True)
        except Supplier.DoesNotExist:
            raise ValidationError(f"Proveedor con ID {entity_id} no encontrado.")

    @classmethod
    def _validate_item(cls, product, quantity, entity):
        if product.supplier_id != entity.id:
            raise ValidationError(
                f"El producto '{product.name}' no pertenece al proveedor '{entity.name}'."
            )

    @classmethod
    def _create_record(cls, entity, user, date, total):
        return Purchase.objects.create(
            supplier=entity,
            user=user,
            date=date,
            total=total,
        )

    @classmethod
    def _build_movement_kwargs(cls, product, user, entity, record, quantity, stock_before, date):
        return {
            'movement_type': MovementType.INPUT,
            'product': product,
            'quantity': quantity,
            'user': user,
            'purchase': record,
            'price': product.price,
            'stock_in_movement': stock_before,
            'date': date,
        }

    @classmethod
    def _apply_stock_change(cls, product, quantity):
        product.current_stock += quantity
