# validators/business_validators.py
"""
Validadores de reglas de negocio reutilizables.
Separan la lógica de validación del modelo/serializer.
"""

from django.core.exceptions import ValidationError
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
        import re
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
        import re
        if not re.match(ValidationMessages.DOCUMENT_REGEX, document):
            raise ValidationError(ValidationMessages.DOCUMENT_INVALID_FORMAT)


class PriceValidator:
    """Validador de precios"""

    @staticmethod
    def validate(price: Decimal) -> None:
        """
        Valida que el precio sea >= 0.

        Args:
            price: Precio a validar

        Raises:
            ValidationError: Si el precio es negativo
        """
        if price < 0:
            raise ValidationError(ValidationMessages.PRICE_NEGATIVE)


class QuantityValidator:
    """Validador de cantidades"""

    @staticmethod
    def validate_positive(quantity: int) -> None:
        """
        Valida que la cantidad sea > 0.

        Args:
            quantity: Cantidad a validar

        Raises:
            ValidationError: Si la cantidad es <= 0
        """
        if quantity is None or quantity <= 0:
            raise ValidationError(ValidationMessages.QUANTITY_INVALID)

    @staticmethod
    def validate_min_one(quantity: int) -> None:
        """
        Valida que la cantidad sea >= 1.

        Args:
            quantity: Cantidad a validar

        Raises:
            ValidationError: Si la cantidad es < 1
        """
        if quantity is None or quantity < 1:
            raise ValidationError(ValidationMessages.QUANTITY_MIN_ONE)


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
