# services/quotation_service.py
"""
Servicio para gestionar lógica de negocio de cotizaciones.
Encapsula operaciones complejas relacionadas con cotizaciones.
"""

from typing import List, Dict
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction

from inventory_app.models import Quotation, QuotedProduct, Product
from inventory_app.constants import BusinessRules, ValidationMessages


class QuotationService:
    """
    Servicio para operaciones de negocio sobre cotizaciones.

    Responsabilidades:
    - Crear cotizaciones con sus productos
    - Validar reglas de negocio
    - Calcular totales (subtotal, IVA, total)
    """

    @staticmethod
    def create_quotation(
        customer_id: int,
        user_id: int,
        products: List[Dict],
        notes: str = ""
    ) -> Quotation:
        """
        Crea una cotización con sus productos asociados.

        Args:
            customer_id: ID del cliente
            user_id: ID del usuario que crea la cotización
            products: Lista de diccionarios con:
                - product_id: ID del producto
                - quantity: Cantidad del producto
                - unit_price: Precio unitario
            notes: Observaciones opcionales

        Returns:
            Quotation: La cotización creada con todos sus productos

        Raises:
            ValidationError: Si las validaciones de negocio fallan

        Example:
            quotation = QuotationService.create_quotation(
                customer_id=1,
                user_id=2,
                products=[
                    {'product_id': 10, 'quantity': 5, 'unit_price': Decimal('100.00')},
                    {'product_id': 11, 'quantity': 2, 'unit_price': Decimal('50.00')},
                ],
                notes='Cotización para cliente preferencial'
            )
        """
        # Validar reglas de negocio
        QuotationService._validate_products(products)

        # Calcular totales
        subtotal = QuotationService._calculate_subtotal(products)
        tax = subtotal * Decimal(str(BusinessRules.TAX_RATE))
        total = subtotal + tax

        # Usar transacción para garantizar atomicidad
        with transaction.atomic():
            # Crear cotización
            quotation = Quotation.objects.create(
                customer_id=customer_id,
                user_id=user_id,
                subtotal=subtotal,
                tax=tax,
                total=total,
                notes=notes
            )

            # Crear productos cotizados
            for product_data in products:
                QuotedProduct.objects.create(
                    quotation=quotation,
                    product_id=product_data['product_id'],
                    quantity=product_data['quantity'],
                    unit_price=product_data['unit_price']
                )

        return quotation

    @staticmethod
    def _validate_products(products: List[Dict]) -> None:
        """
        Valida que los productos cumplan las reglas de negocio.

        Args:
            products: Lista de productos a validar

        Raises:
            ValidationError: Si alguna validación falla
        """
        # Validar que haya al menos un producto
        if not products or len(products) == 0:
            raise ValidationError(ValidationMessages.QUOTATION_MIN_PRODUCTS)

        # Validar que todos los productos existan en la BD
        product_ids = [p.get('product_id') for p in products if p.get('product_id')]
        existing = set(Product.objects.filter(id__in=product_ids).values_list('id', flat=True))
        missing = [pid for pid in product_ids if pid not in existing]
        if missing:
            raise ValidationError(f"Productos no encontrados: {', '.join(str(id) for id in missing)}")

        # Validar cada producto
        for idx, product_data in enumerate(products, start=1):
            quantity = product_data.get('quantity')
            unit_price = product_data.get('unit_price')

            # Validar cantidad
            if quantity is None or quantity <= 0:
                raise ValidationError(
                    ValidationMessages.QUOTATION_PRODUCT_QUANTITY_INVALID.format(index=idx)
                )

            # Validar precio
            if unit_price is None or unit_price < 0:
                raise ValidationError(
                    ValidationMessages.QUOTATION_PRODUCT_PRICE_INVALID.format(index=idx)
                )

    @staticmethod
    def _calculate_subtotal(products: List[Dict]) -> Decimal:
        """
        Calcula el subtotal de los productos.

        Args:
            products: Lista de productos con quantity y unit_price

        Returns:
            Decimal: Subtotal calculado
        """
        subtotal = Decimal('0.00')
        for product_data in products:
            quantity = Decimal(str(product_data['quantity']))
            unit_price = Decimal(str(product_data['unit_price']))
            subtotal += quantity * unit_price

        return subtotal
