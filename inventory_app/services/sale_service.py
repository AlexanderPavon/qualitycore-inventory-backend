# services/sale_service.py
"""
Servicio para gestionar lógica de negocio de ventas.
Hereda la lógica compartida de TransactionServiceBase.
"""

from django.core.exceptions import ValidationError

from inventory_app.models import Sale, Customer
from inventory_app.constants import MovementType
from inventory_app.validators.business_validators import QuantityValidator, StockValidator
from inventory_app.services.transaction_base import TransactionServiceBase


class SaleService(TransactionServiceBase):

    @staticmethod
    def _validate_entity(entity_id):
        try:
            return Customer.objects.get(id=entity_id, deleted_at__isnull=True)
        except Customer.DoesNotExist:
            raise ValidationError(f"Cliente con ID {entity_id} no existe.")

    @staticmethod
    def _validate_item(product, quantity, entity):
        # Las ventas validan cantidad mínima y stock disponible.
        # No se valida ninguna relación cliente-producto porque en este negocio
        # cualquier cliente puede comprar cualquier producto activo.
        # (PurchaseService sí valida supplier-product: el proveedor debe suministrar el producto.)
        QuantityValidator.validate_min_one(quantity)
        StockValidator.validate_availability(product, quantity)

    @staticmethod
    def _create_record(entity, user, date, total):
        return Sale.objects.create(
            customer=entity,
            user=user,
            date=date,
            total=total,
        )

    @staticmethod
    def _build_movement_kwargs(product, user, entity, record, quantity, stock_before, date):
        return {
            'movement_type': MovementType.OUTPUT,
            'product': product,
            'quantity': quantity,
            'user': user,
            'customer': entity,
            'sale': record,
            'price': product.price,
            'stock_in_movement': stock_before,
            'date': date,
        }

    @staticmethod
    def _stock_delta(quantity):
        return -quantity
