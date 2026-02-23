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
    def create_sale(customer_id, user_id, items):
        return SaleService.create(customer_id, user_id, items)

    @classmethod
    def _validate_entity(cls, entity_id):
        try:
            return Customer.objects.get(id=entity_id, deleted_at__isnull=True)
        except Customer.DoesNotExist:
            raise ValidationError(f"Cliente con ID {entity_id} no existe.")

    @classmethod
    def _validate_item(cls, product, quantity, entity):
        QuantityValidator.validate_min_one(quantity)
        StockValidator.validate_availability(product, quantity)

    @classmethod
    def _create_record(cls, entity, user, date, total):
        return Sale.objects.create(
            customer=entity,
            user=user,
            date=date,
            total=total,
        )

    @classmethod
    def _build_movement_kwargs(cls, product, user, entity, record, quantity, stock_before, date):
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

    @classmethod
    def _apply_stock_change(cls, product, quantity):
        product.current_stock -= quantity
