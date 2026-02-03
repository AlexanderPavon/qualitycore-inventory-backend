# services/purchase_service.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Purchase, Movement, Product, Supplier, User
from inventory_app.constants import MovementType
from inventory_app.validators import StockValidator
from inventory_app.services.alert_service import AlertService


class PurchaseService:
    """
    Servicio para gestionar la creación de compras (entradas de inventario).
    Similar a SaleService pero para entradas.
    """

    @staticmethod
    def create_purchase(supplier_id, user_id, items):
        """
        Crea una compra con múltiples productos.
        La fecha se establece automáticamente con la hora exacta del servidor.

        Args:
            supplier_id: ID del proveedor
            user_id: ID del usuario que registra la compra
            items: Lista de dicts con {product: id, quantity: qty}

        Returns:
            Purchase: La compra creada

        Raises:
            ValidationError: Si hay problemas de validación
        """
        # Validar que el proveedor existe
        try:
            supplier = Supplier.objects.get(id=supplier_id, deleted_at__isnull=True)
        except Supplier.DoesNotExist:
            raise ValueError(f"Proveedor con ID {supplier_id} no encontrado.")

        # Validar que el usuario existe
        try:
            user = User.objects.get(id=user_id, deleted_at__isnull=True)
        except User.DoesNotExist:
            raise ValueError(f"Usuario con ID {user_id} no encontrado.")

        # Validar todos los productos y calcular total ANTES de crear nada
        products_data = []
        total = Decimal('0.00')

        for item in items:
            try:
                product = Product.objects.get(id=item['product'], deleted_at__isnull=True)
            except Product.DoesNotExist:
                raise ValueError(f"Producto con ID {item['product']} no encontrado.")

            # Validar que el producto está activo
            if product.status != "Activo":
                raise ValueError(f"El producto '{product.name}' no está activo.")

            quantity = item['quantity']

            # Para entradas no validamos stock, solo registramos
            total += product.price * quantity

            products_data.append({
                'product': product,
                'quantity': quantity
            })

        # Establecer fecha inmutable (hora exacta del servidor)
        transaction_date = timezone.now()

        # Crear la compra y todos los movimientos en una transacción atómica
        with transaction.atomic():
            # Crear la compra
            purchase = Purchase.objects.create(
                supplier=supplier,
                user=user,
                date=transaction_date,
                total=total
            )

            # Crear movimientos para cada producto
            for item_data in products_data:
                product = item_data['product']
                quantity = item_data['quantity']

                # Registrar el stock antes del movimiento
                stock_before = product.current_stock

                # Crear movimiento de entrada
                Movement.objects.create(
                    movement_type=MovementType.INPUT,
                    date=transaction_date,  # Misma fecha inmutable
                    quantity=quantity,
                    product=product,
                    user=user,
                    price=product.price,  # Guardar precio histórico
                    stock_in_movement=stock_before,
                    purchase=purchase  # Relacionar con la compra
                )

                # Actualizar el stock del producto
                product.current_stock += quantity
                product.save()

                # Actualizar alertas de stock
                AlertService.update_stock_alerts(product)

        return purchase
