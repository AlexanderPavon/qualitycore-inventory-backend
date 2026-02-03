# serializers/sale_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from decimal import Decimal

from inventory_app.models.sale import Sale
from inventory_app.models.movement import Movement
from inventory_app.services import SaleService

class SaleItemSerializer(serializers.Serializer):
    """
    Serializer para cada producto en el carrito de una venta.
    """
    product = serializers.IntegerField(help_text="ID del producto")
    quantity = serializers.IntegerField(min_value=1, help_text="Cantidad a vender")

class SaleCreateSerializer(serializers.Serializer):
    """
    Serializer para crear una venta con múltiples productos.
    La fecha se establece automáticamente con la hora exacta del servidor.
    """
    customer = serializers.IntegerField(help_text="ID del cliente")
    items = SaleItemSerializer(many=True, help_text="Lista de productos en el carrito")

    def validate_items(self, value):
        """
        Valida que haya al menos un producto en el carrito.
        """
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe incluir al menos un producto en la venta.")
        return value

    def create(self, validated_data):
        """
        Crea una venta con múltiples productos delegando al servicio.
        La fecha se establece automáticamente en el servicio.
        """
        customer_id = validated_data.get('customer')
        items = validated_data.get('items')

        # Obtener user_id del contexto (pasado desde la vista)
        user_id = self.context.get('user_id')
        if not user_id:
            raise serializers.ValidationError("Usuario no identificado.")

        try:
            # Delegar creación al servicio (lógica de negocio)
            # La fecha se establece automáticamente como timezone.now()
            sale = SaleService.create_sale(
                customer_id=customer_id,
                user_id=user_id,
                items=items
            )
            return sale

        except DjangoValidationError as e:
            # Convertir ValidationError de Django a DRF
            raise serializers.ValidationError(str(e))

class SaleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar detalles de una venta.
    """
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    movements = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'customer', 'customer_name', 'user', 'user_name',
            'date', 'total', 'movements', 'created_at'
        ]

    def get_movements(self, obj):
        """
        Retorna los movimientos asociados a esta venta.
        """
        movements = obj.movements.all()
        return [{
            'id': m.id,
            'product_name': m.product.name,
            'quantity': m.quantity,
            'price': m.price,  # Usar precio histórico del movimiento
            'subtotal': m.price * m.quantity
        } for m in movements]
