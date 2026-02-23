# services/movement_service.py
"""
Servicio para gestionar lógica de negocio de movimientos de inventario.
Encapsula operaciones relacionadas con entradas y salidas de stock.
"""

from typing import Optional
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from inventory_app.models import Movement, Product, Customer, User, Sale, Purchase
from inventory_app.models.audit_log import AuditLog
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
        date=None,
        reason: str = '',
        request=None,
    ) -> Movement:
        """
        Crea un movimiento de inventario (entrada, salida o ajuste).

        Args:
            movement_type: Tipo de movimiento ('input', 'output' o 'adjustment')
            product_id: ID del producto
            quantity: Cantidad del movimiento (positivo para input/output, con signo para adjustment)
            user_id: ID del usuario que registra el movimiento
            customer_id: ID del cliente (requerido para salidas)
            date: Fecha del movimiento (opcional, usa ahora por defecto)
            reason: Motivo del ajuste (obligatorio para tipo adjustment)
            request: Objeto request de Django (para AuditLog)

        Returns:
            Movement: El movimiento creado

        Raises:
            ValidationError: Si las validaciones de negocio fallan
        """
        # Validaciones previas según tipo
        if movement_type in (MovementType.INPUT, MovementType.OUTPUT):
            QuantityValidator.validate_min_one(quantity)
        elif movement_type == MovementType.ADJUSTMENT:
            if quantity == 0:
                raise ValidationError(ValidationMessages.ADJUSTMENT_QUANTITY_NONZERO)
            if not reason or not reason.strip():
                raise ValidationError(ValidationMessages.ADJUSTMENT_REASON_REQUIRED)

        # Transacción atómica con lock de fila para prevenir race conditions
        with transaction.atomic():
            # Obtener producto con lock exclusivo
            try:
                product = Product.objects.select_for_update().get(id=product_id)
            except Product.DoesNotExist:
                raise ValidationError(f"Producto con ID {product_id} no existe.")

            # Validaciones específicas por tipo de movimiento
            if movement_type == MovementType.OUTPUT:
                MovementService._validate_output(product, quantity, customer_id)
            elif movement_type == MovementType.INPUT:
                MovementService._validate_input()
            elif movement_type == MovementType.ADJUSTMENT:
                MovementService._validate_adjustment(product, quantity)

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
                date=date or timezone.now(),
                reason=reason,
            )

            # Actualizar stock del producto
            MovementService._update_product_stock(product, movement_type, quantity)

            # Actualizar alertas de stock
            AlertService.update_stock_alerts(product)

            # Registrar en audit log para ajustes
            if movement_type == MovementType.ADJUSTMENT:
                AuditLog.log_action(
                    user=User.objects.get(id=user_id),
                    action='create',
                    model_name='Movement',
                    obj=movement,
                    changes={
                        'movement_type': 'adjustment',
                        'product_id': product.id,
                        'product_name': product.name,
                        'stock_before': stock_before,
                        'stock_after': product.current_stock,
                        'quantity': quantity,
                        'reason': reason,
                    },
                    request=request,
                )

        return movement

    @staticmethod
    def create_correction(
        original_movement_id: int,
        new_quantity: int,
        reason: str,
        user_id: int,
        request=None,
    ) -> Movement:
        """
        Corrige un movimiento existente (entrada o salida).
        Crea un movimiento de corrección que ajusta la diferencia de stock
        y marca el original como corregido.

        Args:
            original_movement_id: ID del movimiento a corregir
            new_quantity: La cantidad correcta (siempre positiva)
            reason: Motivo de la corrección
            user_id: ID del usuario que realiza la corrección
            request: Objeto request de Django (para AuditLog)

        Returns:
            Movement: El movimiento de corrección creado
        """
        if not reason or not reason.strip():
            raise ValidationError(ValidationMessages.CORRECTION_REASON_REQUIRED)

        with transaction.atomic():
            try:
                original = Movement.objects.select_for_update().get(
                    id=original_movement_id, deleted_at__isnull=True
                )
            except Movement.DoesNotExist:
                raise ValidationError(f"Movimiento con ID {original_movement_id} no existe.")

            # Validar que no haya sido corregido ya
            if original.corrected_by is not None:
                raise ValidationError(ValidationMessages.CORRECTION_ALREADY_CORRECTED)

            # Solo se pueden corregir entradas y salidas
            if original.movement_type not in (MovementType.INPUT, MovementType.OUTPUT):
                raise ValidationError(ValidationMessages.CORRECTION_INVALID_TYPE)

            # Validar que la cantidad sea diferente
            if new_quantity == original.quantity:
                raise ValidationError(ValidationMessages.CORRECTION_SAME_QUANTITY)

            # Validar cantidad positiva
            QuantityValidator.validate_min_one(new_quantity)

            product = Product.objects.select_for_update().get(id=original.product_id)

            # Calcular diferencia de stock
            # Input original sumó N al stock → corrección = new_quantity - original
            # Output original restó N del stock → corrección = original - new_quantity
            if original.movement_type == MovementType.INPUT:
                stock_diff = new_quantity - original.quantity
            else:  # OUTPUT
                stock_diff = original.quantity - new_quantity

            # Validar que no quede stock negativo
            if product.current_stock + stock_diff < 0:
                raise ValidationError(ValidationMessages.CORRECTION_STOCK_NEGATIVE)

            stock_before = product.current_stock

            # Crear movimiento de corrección
            correction = Movement.objects.create(
                movement_type=MovementType.CORRECTION,
                product=product,
                quantity=stock_diff,
                user_id=user_id,
                stock_in_movement=stock_before,
                date=timezone.now(),
                reason=reason.strip(),
                sale=original.sale,
                purchase=original.purchase,
                customer=original.customer,
            )

            # Actualizar stock
            product.current_stock += stock_diff
            product.save()

            # Marcar original como corregido
            original.corrected_by = correction
            original.save(update_fields=['corrected_by', 'updated_at'])

            # Recalcular total de la venta/compra
            total_diff = (new_quantity - original.quantity) * original.price
            if original.sale_id:
                Sale.objects.filter(id=original.sale_id).update(
                    total=models.F('total') + total_diff
                )
            elif original.purchase_id:
                Purchase.objects.filter(id=original.purchase_id).update(
                    total=models.F('total') + total_diff
                )

            # Actualizar alertas de stock
            AlertService.update_stock_alerts(product)

            # Registrar en audit log
            AuditLog.log_action(
                user=User.objects.get(id=user_id),
                action='create',
                model_name='Movement',
                obj=correction,
                changes={
                    'movement_type': 'correction',
                    'original_movement_id': original.id,
                    'product_id': product.id,
                    'product_name': product.name,
                    'original_quantity': original.quantity,
                    'new_quantity': new_quantity,
                    'stock_diff': stock_diff,
                    'stock_before': stock_before,
                    'stock_after': product.current_stock,
                    'reason': reason.strip(),
                },
                request=request,
            )

        return correction

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
    def _validate_adjustment(product: Product, quantity: int) -> None:
        """
        Validaciones específicas para movimientos de ajuste.
        Si es negativo, verifica que haya stock suficiente.
        """
        if quantity < 0:
            requested = abs(quantity)
            if requested > product.current_stock:
                raise ValidationError(
                    ValidationMessages.ADJUSTMENT_STOCK_INSUFFICIENT.format(
                        available=product.current_stock,
                        requested=requested,
                    )
                )

    @staticmethod
    def _update_product_stock(product: Product, movement_type: str, quantity: int) -> None:
        """
        Actualiza el stock del producto según el tipo de movimiento.

        Args:
            product: Producto a actualizar
            movement_type: Tipo de movimiento ('input', 'output' o 'adjustment')
            quantity: Cantidad del movimiento
        """
        if movement_type == MovementType.INPUT:
            product.current_stock += quantity
        elif movement_type == MovementType.OUTPUT:
            product.current_stock -= quantity
        elif movement_type == MovementType.ADJUSTMENT:
            product.current_stock += quantity  # quantity con signo: +5 agrega, -5 reduce

        product.save()
