# services/purchase_service.py
"""
Servicio para gestionar lógica de negocio de compras.
Hereda la lógica compartida de TransactionServiceBase.
"""

from django.core.exceptions import ValidationError

from inventory_app.models import Purchase, Supplier
from inventory_app.constants import MovementType
from inventory_app.services.transaction_base import TransactionServiceBase
from inventory_app.validators.business_validators import QuantityValidator


class PurchaseService(TransactionServiceBase):

    @staticmethod
    def _validate_entity(entity_id):
        try:
            return Supplier.objects.get(id=entity_id, deleted_at__isnull=True)
        except Supplier.DoesNotExist:
            raise ValidationError(f"Proveedor con ID {entity_id} no encontrado.")

    @staticmethod
    def _validate_item(product, quantity, entity):
        QuantityValidator.validate_min_one(quantity)
        if product.supplier_id != entity.id:
            raise ValidationError(
                f"El producto '{product.name}' no pertenece al proveedor '{entity.name}'."
            )

    @staticmethod
    def _create_record(entity, user, date, total):
        return Purchase.objects.create(
            supplier=entity,
            user=user,
            date=date,
            total=total,
        )

    @staticmethod
    def _build_movement_kwargs(product, user, entity, record, quantity, stock_before, date):
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

    @staticmethod
    def _stock_delta(quantity):
        return quantity
