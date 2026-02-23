# services/transaction_base.py
"""
Lógica compartida para crear transacciones (ventas y compras).
Ambas siguen el mismo patrón: validar → transacción atómica → crear entidad
→ crear movimientos → actualizar stock → alertas.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Movement, Product, User
from inventory_app.services.alert_service import AlertService

import logging

logger = logging.getLogger(__name__)


class TransactionServiceBase:
    """
    Clase base con la lógica compartida entre SaleService y PurchaseService.

    Las subclases deben implementar:
    - _validate_entity(entity_id): valida y retorna la entidad (customer/supplier)
    - _validate_item(product, item, entity): validaciones específicas del item
    - _create_record(entity, user, date, total): crea Sale/Purchase
    - _build_movement_kwargs(product, user, entity, record, ...): kwargs para Movement
    - _apply_stock_change(product, quantity): +/- stock
    - movement_type: str - tipo de movimiento ('input'/'output')
    """

    @classmethod
    def create(cls, entity_id, user_id, items):
        if not items:
            raise ValidationError("La transacción debe incluir al menos un producto.")

        # Validar entidad (customer o supplier)
        entity = cls._validate_entity(entity_id)

        # Validar usuario
        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            raise ValidationError(f"Usuario con ID {user_id} no existe.")

        transaction_date = timezone.now()

        with transaction.atomic():
            products_data = []
            total = Decimal('0.00')

            for item in items:
                product_id = item.get('product')
                quantity = item.get('quantity')

                try:
                    product = Product.objects.select_for_update().get(
                        id=product_id, deleted_at__isnull=True
                    )
                except Product.DoesNotExist:
                    raise ValidationError(f"Producto con ID {product_id} no existe.")

                # Validaciones específicas (stock para ventas, proveedor para compras)
                cls._validate_item(product, quantity, entity)

                subtotal = product.price * quantity
                total += subtotal

                products_data.append({
                    'product': product,
                    'quantity': quantity,
                    'stock_before': product.current_stock,
                })

            # Crear registro (Sale o Purchase)
            record = cls._create_record(entity, user, transaction_date, total)

            # Crear movimientos y actualizar stock
            for item_data in products_data:
                product = item_data['product']
                quantity = item_data['quantity']

                movement_kwargs = cls._build_movement_kwargs(
                    product=product,
                    user=user,
                    entity=entity,
                    record=record,
                    quantity=quantity,
                    stock_before=item_data['stock_before'],
                    date=transaction_date,
                )
                Movement.objects.create(**movement_kwargs)

                cls._apply_stock_change(product, quantity)
                product.save()

                AlertService.update_stock_alerts(product)

            logger.info(
                f"{cls.__name__}: #{record.id} creada con "
                f"{len(products_data)} productos. Total: ${total}"
            )

        return record

    @classmethod
    def _validate_entity(cls, entity_id):
        raise NotImplementedError

    @classmethod
    def _validate_item(cls, product, quantity, entity):
        raise NotImplementedError

    @classmethod
    def _create_record(cls, entity, user, date, total):
        raise NotImplementedError

    @classmethod
    def _build_movement_kwargs(cls, product, user, entity, record, quantity, stock_before, date):
        raise NotImplementedError

    @classmethod
    def _apply_stock_change(cls, product, quantity):
        raise NotImplementedError
