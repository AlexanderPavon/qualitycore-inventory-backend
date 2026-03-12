# validators/business_validators.py
"""
Validadores de reglas de negocio reutilizables.
Separan la lógica de validación del modelo/serializer.
"""

import re

from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from typing import Optional
from inventory_app.constants import ValidationMessages, BusinessRules


class PhoneValidator:
    """Validador de teléfonos Ecuador (10 dígitos)"""

    @staticmethod
    def validate(phone: str) -> None:
        """
        Valida formato de teléfono Ecuador.

        Args:
            phone: Número de teléfono a validar

        Raises:
            ValidationError: Si el teléfono no cumple el formato
        """
        if not re.match(ValidationMessages.PHONE_REGEX, phone):
            raise ValidationError(ValidationMessages.PHONE_INVALID_FORMAT)


class DocumentValidator:
    """Validador de cédula/RUC Ecuador"""

    @staticmethod
    def validate(document: str) -> None:
        """
        Valida formato de cédula o RUC Ecuador.

        Args:
            document: Cédula o RUC a validar

        Raises:
            ValidationError: Si el documento no cumple el formato
        """
        if not re.match(ValidationMessages.DOCUMENT_REGEX, document):
            raise ValidationError(ValidationMessages.DOCUMENT_INVALID_FORMAT)


class PriceValidator:
    """Validador de precios"""

    @staticmethod
    def validate(price: Decimal) -> None:
        """
        Valida que el precio esté en el rango [0, BusinessRules.MAX_PRODUCT_PRICE].

        Args:
            price: Precio a validar

        Raises:
            ValidationError: Si el precio es negativo o excede el límite máximo
        """
        if price < 0:
            raise ValidationError(ValidationMessages.PRICE_NEGATIVE)
        if price > Decimal(str(BusinessRules.MAX_PRODUCT_PRICE)):
            raise ValidationError(
                f"El precio no puede exceder ${BusinessRules.MAX_PRODUCT_PRICE:,.2f}."
            )


class QuantityValidator:
    """Validador de cantidades"""

    @staticmethod
    def validate_min_one(quantity: int) -> None:
        """
        Valida que la cantidad sea >= 1.
        Para enteros (el único tipo que maneja el sistema), qty >= 1 equivale a qty > 0.

        Args:
            quantity: Cantidad a validar

        Raises:
            ValidationError: Si la cantidad es < 1
        """
        if quantity is None or quantity < 1:
            raise ValidationError(ValidationMessages.QUANTITY_MIN_ONE)


class MovementDateValidator:
    """Valida que la fecha de un movimiento sea del día actual (no futura, no pasada)."""

    @staticmethod
    def validate(value) -> None:
        """
        Raises ValidationError si la fecha es futura o de un día anterior al actual.
        Compartida entre MovementSerializer y MovementAdjustmentSerializer.
        """
        now = timezone.now()
        if value > now:
            raise ValidationError("La fecha del movimiento no puede ser futura.")
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if value < today_start:
            raise ValidationError(
                "Solo se pueden registrar movimientos del día actual. "
                "No se permiten fechas de días anteriores."
            )


class StockValidator:
    """Validador de inventario/stock"""

    @staticmethod
    def validate_availability(product, requested_quantity: int) -> None:
        """
        Valida que haya stock suficiente para una salida.

        Args:
            product: Producto a validar
            requested_quantity: Cantidad solicitada

        Raises:
            ValidationError: Si no hay stock suficiente
        """
        if requested_quantity > product.current_stock:
            raise ValidationError(
                ValidationMessages.STOCK_INSUFFICIENT.format(
                    available=product.current_stock,
                    requested=requested_quantity
                )
            )
