# services/movement_service.py
"""
Servicio para gestionar lógica de negocio de movimientos de inventario.
Encapsula operaciones relacionadas con entradas y salidas de stock.
"""

import logging
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from inventory_app.models import Movement, Product, Customer, User, Sale, Purchase
from inventory_app.models.audit_log import AuditLog
from inventory_app.constants import MovementType, ValidationMessages, BusinessRules
from inventory_app.validators.business_validators import QuantityValidator, StockValidator
from inventory_app.services.alert_service import AlertService

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
        Crea un movimiento de inventario de tipo 'adjustment' o 'correction'.

        Los tipos 'input' y 'output' están explícitamente prohibidos aquí porque
        requieren una Purchase/Sale vinculada (constraint de DB). Esos flujos deben
        ir por PurchaseService.create() / SaleService.create() respectivamente.

        Args:
            movement_type: Tipo de movimiento ('adjustment' o 'correction')
            product_id: ID del producto
            quantity: Cantidad del movimiento (con signo para adjustment: +5 suma, -5 resta)
            user_id: ID del usuario que registra el movimiento
            customer_id: ID del cliente (no usado en adjustments/corrections)
            date: Fecha del movimiento (opcional, usa ahora por defecto)
            reason: Motivo del ajuste/corrección (obligatorio)
            request: Objeto request de Django (para AuditLog)

        Returns:
            Movement: El movimiento creado

        Raises:
            ValidationError: Si las validaciones de negocio fallan
        """
        # INPUT y OUTPUT tienen constraints de DB que requieren purchase/sale vinculados.
        # Llamar create_movement('input/output') directamente produce IntegrityError en
        # producción (PostgreSQL) aunque los tests pasen en SQLite.
        if movement_type in (MovementType.INPUT, MovementType.OUTPUT):
            raise ValidationError(
                f"'{movement_type}' no está permitido en create_movement(). "
                "Usa PurchaseService.create() para entradas o "
                "SaleService.create() para salidas."
            )

        # Validaciones previas según tipo
        if movement_type == MovementType.ADJUSTMENT:
            if quantity == 0:
                raise ValidationError(ValidationMessages.ADJUSTMENT_QUANTITY_NONZERO)
            if not reason or not reason.strip():
                raise ValidationError(ValidationMessages.ADJUSTMENT_REASON_REQUIRED)

        # Obtener usuario antes del bloque atómico: evita una query extra dentro de la
        # transacción mientras el lock de Product está activo. Mismo patrón que
        # create_correction() para minimizar el tiempo de contención.
        try:
            audit_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError(f"Usuario con ID {user_id} no existe.")

        # Transacción atómica con lock de fila para prevenir race conditions
        with transaction.atomic():
            # Obtener producto con lock exclusivo
            try:
                product = Product.objects.select_for_update().get(id=product_id)
            except Product.DoesNotExist:
                raise ValidationError(f"Producto con ID {product_id} no existe.")

            # Validaciones específicas por tipo de movimiento (solo adjustment llega aquí)
            if movement_type == MovementType.ADJUSTMENT:
                MovementService._validate_adjustment(product, quantity)

            # Guardar stock actual antes del movimiento
            stock_before = product.current_stock

            # Crear movimiento con _skip_audit=True para que el signal post_save
            # no duplique el registro — el AuditLog.log_action de abajo incluye
            # datos más ricos (stock_after, customer_id) que el signal no puede capturar.
            movement = Movement(
                movement_type=movement_type,
                product=product,
                quantity=quantity,
                user_id=user_id,
                customer_id=customer_id,
                stock_in_movement=stock_before,
                date=date or timezone.now(),
                reason=reason,
            )
            movement._skip_audit = True
            movement.save()

            # Actualizar stock del producto
            MovementService._update_product_stock(product, movement_type, quantity)

            # Actualizar alertas de stock
            AlertService.update_stock_alerts(product)

            # Registrar en audit log con datos ricos (stock_after disponible tras
            # _update_product_stock; customer_id solo para salidas)
            extra = {'customer_id': customer_id} if customer_id else {}
            AuditLog.log_action(
                user=audit_user,
                action='create',
                model_name='Movement',
                obj=movement,
                changes={
                    'movement_type': movement_type,
                    'product_id': product.id,
                    'product_name': product.name,
                    'stock_before': stock_before,
                    'stock_after': product.current_stock,
                    'quantity': quantity,
                    'reason': reason,
                    **extra,
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

        # Obtener user antes del bloque atómico: evita una query extra dentro de la
        # transacción y previene un DoesNotExist tardío si el user fue eliminado.
        try:
            audit_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError(f"Usuario con ID {user_id} no existe.")

        with transaction.atomic():
            try:
                original = Movement.objects.select_for_update().get(
                    id=original_movement_id, deleted_at__isnull=True
                )
            except Movement.DoesNotExist:
                raise ValidationError(f"Movimiento con ID {original_movement_id} no existe.")

            # Validar que no haya sido corregido ya
            if original.correction is not None:
                raise ValidationError(ValidationMessages.CORRECTION_ALREADY_CORRECTED)

            # Validar que el movimiento no sea demasiado antiguo
            age_days = (timezone.now() - original.date).days
            if age_days > BusinessRules.MAX_CORRECTION_AGE_DAYS:
                raise ValidationError(
                    ValidationMessages.CORRECTION_TOO_OLD.format(
                        days=BusinessRules.MAX_CORRECTION_AGE_DAYS
                    )
                )

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

            # Crear movimiento de corrección con _skip_audit=True para que el signal
            # no duplique el registro — el AuditLog.log_action de abajo incluye datos
            # únicos (original_movement_id, original_quantity) no almacenados en el objeto.
            correction = Movement(
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
            correction._skip_audit = True
            correction.save()

            # Actualizar stock con F() para evitar race conditions
            Product.objects.filter(id=product.id).update(
                current_stock=models.F('current_stock') + stock_diff
            )
            product.refresh_from_db(fields=['current_stock'])

            # Marcar original como corregido
            original.correction = correction
            original.save(update_fields=['correction', 'updated_at'])

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
                user=audit_user,
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
        Usa UPDATE + F() para evitar race conditions entre requests simultáneos.

        Args:
            product: Producto a actualizar (se hace refresh_from_db tras el UPDATE)
            movement_type: Tipo de movimiento ('input', 'output' o 'adjustment')
            quantity: Cantidad del movimiento (quantity con signo para adjustment)
        """
        if movement_type == MovementType.INPUT:
            delta = quantity
        elif movement_type == MovementType.OUTPUT:
            delta = -quantity
        elif movement_type == MovementType.ADJUSTMENT:
            delta = quantity  # quantity ya tiene signo: +5 agrega, -5 reduce
        else:
            return

        Product.objects.filter(id=product.id).update(
            current_stock=models.F('current_stock') + delta
        )
        product.refresh_from_db(fields=['current_stock'])
