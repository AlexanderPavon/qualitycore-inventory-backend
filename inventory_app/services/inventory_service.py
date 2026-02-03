# services/inventory_service.py
"""
Servicio de lógica de negocio para operaciones de inventario.
Centraliza toda la lógica relacionada con movimientos de stock y alertas.
"""
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from rest_framework.exceptions import ValidationError
from inventory_app.models.product import Product
from inventory_app.models.movement import Movement
from inventory_app.models.alert import Alert
from inventory_app.services.alert_service import AlertService
import logging

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Servicio para manejar operaciones de inventario de manera centralizada.
    Todas las operaciones son atómicas usando transacciones de Django.
    """

    @staticmethod
    @transaction.atomic
    def register_movement(product_id, quantity, movement_type, user, customer=None, date=None):
        """
        Registra un movimiento de inventario (entrada o salida).

        Args:
            product_id: ID del producto
            quantity: Cantidad a mover
            movement_type: 'input' o 'output'
            user: Usuario que registra el movimiento
            customer: Cliente (opcional, para salidas)
            date: Fecha del movimiento (opcional, usa fecha actual si no se proporciona)

        Returns:
            Movement: El movimiento creado

        Raises:
            ValidationError: Si el stock es insuficiente o datos inválidos
        """
        # Si no se proporciona fecha, usar la fecha actual
        if date is None:
            from django.utils import timezone as tz
            date = tz.now()
        movement_type = movement_type.lower()

        # Bloquear el producto para evitar race conditions
        try:
            product = Product.objects.select_for_update().get(pk=product_id)
        except Product.DoesNotExist:
            logger.error(f"Producto {product_id} no encontrado")
            raise ValidationError("El producto no existe.")

        # Validar stock disponible ANTES de realizar la operación
        if movement_type == "output":
            if quantity > product.current_stock:
                logger.warning(
                    f"Stock insuficiente para producto {product.name}. "
                    f"Solicitado: {quantity}, Disponible: {product.current_stock}"
                )
                raise ValidationError(
                    f"Stock insuficiente. Disponible: {product.current_stock}, Solicitado: {quantity}"
                )

        # Actualizar stock usando F() expressions para operación atómica a nivel de DB
        if movement_type == "input":
            Product.objects.filter(pk=product.id).update(
                current_stock=F('current_stock') + quantity
            )
            logger.info(f"Entrada de {quantity} unidades de {product.name}")
        elif movement_type == "output":
            Product.objects.filter(pk=product.id).update(
                current_stock=F('current_stock') - quantity
            )
            logger.info(f"Salida de {quantity} unidades de {product.name}")
        else:
            raise ValidationError("Tipo de movimiento inválido. Use 'input' o 'output'.")

        # Refrescar el producto para obtener el nuevo stock
        product.refresh_from_db()

        # Crear el movimiento
        movement = Movement.objects.create(
            product=product,
            quantity=quantity,
            movement_type=movement_type,
            user=user,
            date=date,
            customer=customer,
            stock_in_movement=product.current_stock
        )

        # Actualizar alertas de stock usando el servicio centralizado
        AlertService.update_stock_alerts(product)

        # Invalidar caché del dashboard cuando se crea un movimiento
        cache.delete('dashboard_summary')
        logger.info("Dashboard cache invalidated after movement creation")

        logger.info(
            f"Movimiento registrado: {movement_type} de {quantity} unidades "
            f"de {product.name}. Stock actual: {product.current_stock}"
        )

        return movement

    @staticmethod
    def get_low_stock_products(threshold=None):
        """
        Obtiene todos los productos con stock bajo.

        Args:
            threshold: Umbral personalizado (opcional). Si no se proporciona,
                      usa el minimum_stock de cada producto.

        Returns:
            QuerySet de productos con stock bajo
        """
        if threshold is not None:
            return Product.objects.filter(
                deleted_at__isnull=True,
                current_stock__lte=threshold
            )
        else:
            return Product.objects.filter(
                deleted_at__isnull=True,
                current_stock__lte=F('minimum_stock')
            )

    @staticmethod
    def check_stock_availability(product_id, quantity):
        """
        Verifica si hay suficiente stock disponible para un producto.

        Args:
            product_id: ID del producto
            quantity: Cantidad requerida

        Returns:
            tuple: (bool, int) - (disponible, stock_actual)
        """
        try:
            product = Product.objects.get(pk=product_id, deleted_at__isnull=True)
            return (product.current_stock >= quantity, product.current_stock)
        except Product.DoesNotExist:
            return (False, 0)


# Importar timezone al final para evitar importación circular
from django.utils import timezone
