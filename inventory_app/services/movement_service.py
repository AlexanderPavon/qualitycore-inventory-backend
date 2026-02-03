# services/movement_service.py
"""
Servicio para gestionar lógica de negocio de movimientos de inventario.
Encapsula operaciones relacionadas con entradas y salidas de stock.
"""

from typing import Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory_app.models import Movement, Product, Customer, User
from inventory_app.constants import MovementType, ValidationMessages
from inventory_app.validators.business_validators import QuantityValidator, StockValidator
from inventory_app.services.alert_service import AlertService

import logging

logger = logging.getLogger(__name__)


class MovementService:
    """
    Servicio para operaciones de negocio sobre movimientos de inventario.

    Responsabilidades:
    - Crear movimientos de entrada/salida
    - Validar disponibilidad de stock
    - Actualizar stock del producto
    """

    @staticmethod
    def create_movement(
        movement_type: str,
        product_id: int,
        quantity: int,
        user_id: int,
        customer_id: Optional[int] = None,
        date=None
    ) -> Movement:
        """
        Crea un movimiento de inventario (entrada o salida).

        Args:
            movement_type: Tipo de movimiento ('input' o 'output')
            product_id: ID del producto
            quantity: Cantidad del movimiento
            user_id: ID del usuario que registra el movimiento
            customer_id: ID del cliente (requerido para salidas)
            date: Fecha del movimiento (opcional, usa ahora por defecto)

        Returns:
            Movement: El movimiento creado

        Raises:
            ValidationError: Si las validaciones de negocio fallan

        Example:
            # Crear entrada de inventario
            movement = MovementService.create_movement(
                movement_type=MovementType.INPUT,
                product_id=10,
                quantity=50,
                user_id=1
            )

            # Crear salida de inventario
            movement = MovementService.create_movement(
                movement_type=MovementType.OUTPUT,
                product_id=10,
                quantity=5,
                user_id=1,
                customer_id=3
            )
        """
        from django.utils import timezone

        # Obtener producto
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con ID {product_id} no existe.")

        # Validar cantidad
        QuantityValidator.validate_min_one(quantity)

        # Validaciones específicas por tipo de movimiento
        if movement_type == MovementType.OUTPUT:
            MovementService._validate_output(product, quantity, customer_id)
        elif movement_type == MovementType.INPUT:
            MovementService._validate_input()

        # Usar transacción para garantizar atomicidad
        with transaction.atomic():
            # Guardar stock actual antes del movimiento
            stock_before = product.current_stock

            # Crear movimiento
            movement = Movement.objects.create(
                movement_type=movement_type,
                product=product,
                quantity=quantity,
                user_id=user_id,
                customer_id=customer_id,
                stock_in_movement=stock_before,
                date=date or timezone.now()
            )

            # Actualizar stock del producto
            MovementService._update_product_stock(product, movement_type, quantity)

            # Actualizar alertas de stock
            AlertService.update_stock_alerts(product)

        return movement

    @staticmethod
    def _validate_output(product: Product, quantity: int, customer_id: Optional[int]) -> None:
        """
        Validaciones específicas para movimientos de salida.

        Args:
            product: Producto del movimiento
            quantity: Cantidad solicitada
            customer_id: ID del cliente

        Raises:
            ValidationError: Si alguna validación falla
        """
        # Validar que hay stock suficiente
        StockValidator.validate_availability(product, quantity)

        # Validar que se especificó cliente
        if not customer_id:
            raise ValidationError(ValidationMessages.MOVEMENT_CUSTOMER_REQUIRED)

    @staticmethod
    def _validate_input() -> None:
        """
        Validaciones específicas para movimientos de entrada.
        Por ahora no hay validaciones adicionales para entradas.
        """
        pass

    @staticmethod
    def _update_product_stock(product: Product, movement_type: str, quantity: int) -> None:
        """
        Actualiza el stock del producto según el tipo de movimiento.

        Args:
            product: Producto a actualizar
            movement_type: Tipo de movimiento ('input' o 'output')
            quantity: Cantidad del movimiento
        """
        if movement_type == MovementType.INPUT:
            product.current_stock += quantity
        elif movement_type == MovementType.OUTPUT:
            product.current_stock -= quantity

        product.save()
