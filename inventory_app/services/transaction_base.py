# services/transaction_base.py
"""
Lógica compartida para crear transacciones (ventas y compras).
Ambas siguen el mismo patrón: validar → transacción atómica → crear entidad
→ crear movimientos → actualizar stock → alertas.
"""

from abc import ABC, abstractmethod
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Movement, Product, User
from inventory_app.services.alert_service import AlertService
from inventory_app.services.dashboard_service import DASHBOARD_CACHE_KEY

import logging

logger = logging.getLogger(__name__)


class TransactionServiceBase(ABC):
    """
    Clase base con la lógica compartida entre SaleService y PurchaseService.

    Las subclases deben implementar:
    - _validate_entity(entity_id): valida y retorna la entidad (customer/supplier)
    - _validate_item(product, item, entity): validaciones específicas del item
    - _create_record(entity, user, date, total): crea Sale/Purchase
    - _build_movement_kwargs(product, user, entity, record, ...): kwargs para Movement
    - _stock_delta(quantity): retorna el delta firmado (+quantity para entradas, -quantity para salidas)
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
            # Bloquear todas las filas de productos de una sola vez antes de validar.
            # Un único SELECT FOR UPDATE con __in evita deadlocks (la BD ordena por PK
            # de forma consistente) y elimina el TOCTOU entre la consulta y la escritura.
            product_ids = [item.get('product') for item in items]
            locked_products = {
                p.id: p
                for p in Product.objects.select_for_update().filter(
                    id__in=product_ids, deleted_at__isnull=True
                )
            }

            products_data = []
            total = Decimal('0.00')

            for item in items:
                product_id = item.get('product')
                quantity = item.get('quantity')

                if product_id not in locked_products:
                    raise ValidationError(f"Producto con ID {product_id} no existe.")

                product = locked_products[product_id]

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

                Product.objects.filter(id=product.id).update(
                    current_stock=F('current_stock') + cls._stock_delta(quantity)
                )
                product.refresh_from_db(fields=['current_stock'])

                AlertService.update_stock_alerts(product)

            logger.info(
                f"{cls.__name__}: #{record.id} creada con "
                f"{len(products_data)} productos. Total: ${total}"
            )

        # Invalidar caché del dashboard para que refleje la nueva transacción
        # inmediatamente (ventas, movimientos, alertas pueden haber cambiado).
        cache.delete(DASHBOARD_CACHE_KEY)

        return record

    @staticmethod
    @abstractmethod
    def _validate_entity(entity_id):
        """Valida y retorna la entidad (Customer o Supplier)."""

    @staticmethod
    @abstractmethod
    def _validate_item(product, quantity, entity):
        """Validaciones específicas del ítem (stock para ventas, proveedor para compras)."""

    @staticmethod
    @abstractmethod
    def _create_record(entity, user, date, total):
        """Crea el registro principal (Sale o Purchase)."""

    @staticmethod
    @abstractmethod
    def _build_movement_kwargs(product, user, entity, record, quantity, stock_before, date):
        """Retorna los kwargs para crear el Movement asociado."""

    @staticmethod
    @abstractmethod
    def _stock_delta(quantity):
        """Retorna el delta firmado a aplicar a current_stock (+quantity entradas, -quantity salidas)."""
