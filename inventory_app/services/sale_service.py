# services/sale_service.py
"""
Servicio para gestionar lógica de negocio de ventas.
Encapsula operaciones relacionadas con la creación de ventas con múltiples productos.
"""

from typing import List, Dict
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Sale, Movement, Product, Customer, User
from inventory_app.constants import MovementType, ValidationMessages
from inventory_app.validators.business_validators import QuantityValidator, StockValidator
from inventory_app.services.alert_service import AlertService

import logging

logger = logging.getLogger(__name__)


class SaleService:
    """
    Servicio para operaciones de negocio sobre ventas.

    Responsabilidades:
    - Crear ventas con múltiples productos
    - Validar disponibilidad de stock para todos los productos
    - Crear movimientos asociados a la venta
    - Garantizar atomicidad de la transacción
    """

    @staticmethod
    def create_sale(
        customer_id: int,
        user_id: int,
        items: List[Dict]
    ) -> Sale:
        """
        Crea una venta con múltiples productos de forma atómica.
        La fecha se establece automáticamente con la hora exacta del servidor.

        Args:
            customer_id: ID del cliente que compra
            user_id: ID del usuario que registra la venta
            items: Lista de diccionarios con 'product' (ID) y 'quantity'

        Returns:
            Sale: La venta creada con sus movimientos asociados

        Raises:
            ValidationError: Si alguna validación falla

        Example:
            sale = SaleService.create_sale(
                customer_id=1,
                user_id=2,
                items=[
                    {'product': 10, 'quantity': 5},
                    {'product': 15, 'quantity': 3}
                ]
            )
        """
        # Validar que hay productos en el carrito
        if not items or len(items) == 0:
            raise ValidationError("La venta debe incluir al menos un producto.")

        # Obtener instancias necesarias
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise ValidationError(f"Cliente con ID {customer_id} no existe.")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError(f"Usuario con ID {user_id} no existe.")

        # Validar cantidades antes de la transacción
        for item in items:
            QuantityValidator.validate_min_one(item.get('quantity'))

        # Establecer fecha inmutable (hora exacta del servidor)
        transaction_date = timezone.now()

        # Toda la validación y creación dentro de una transacción atómica
        # con select_for_update para evitar race conditions de stock
        with transaction.atomic():
            products_data = []
            total = Decimal('0.00')

            for item in items:
                product_id = item.get('product')
                quantity = item.get('quantity')

                # Obtener producto con bloqueo para evitar race conditions
                try:
                    product = Product.objects.select_for_update().get(id=product_id)
                except Product.DoesNotExist:
                    raise ValidationError(f"Producto con ID {product_id} no existe.")

                # Validar stock disponible (con datos bloqueados/actualizados)
                StockValidator.validate_availability(product, quantity)

                subtotal = product.price * quantity
                total += subtotal

                products_data.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'stock_before': product.current_stock
                })

            # Crear la venta
            sale = Sale.objects.create(
                customer=customer,
                user=user,
                date=transaction_date,
                total=total
            )

            # Crear movimientos para cada producto
            for item_data in products_data:
                product = item_data['product']
                quantity = item_data['quantity']
                stock_before = item_data['stock_before']

                Movement.objects.create(
                    movement_type=MovementType.OUTPUT,
                    product=product,
                    quantity=quantity,
                    user=user,
                    customer=customer,
                    sale=sale,
                    price=product.price,
                    stock_in_movement=stock_before,
                    date=transaction_date
                )

                # Actualizar stock del producto
                product.current_stock -= quantity
                product.save()

                # Actualizar alertas de bajo stock
                AlertService.update_stock_alerts(product)

            logger.info(f"Venta #{sale.id} creada con {len(products_data)} productos. Total: ${total}")

        return sale
