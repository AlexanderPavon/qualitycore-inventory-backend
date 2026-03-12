# serializers/sale_serializer.py
from rest_framework import serializers

from inventory_app.models.sale import Sale
from inventory_app.services import SaleService
from inventory_app.serializers.mixins import InvoiceMovementsMixin, TransactionSerializerMixin


class SaleItemSerializer(serializers.Serializer):
    """
    Serializer para cada producto en el carrito de una venta.
    """
    product = serializers.IntegerField(help_text="ID del producto")
    quantity = serializers.IntegerField(min_value=1, help_text="Cantidad a vender")


class SaleCreateSerializer(TransactionSerializerMixin):
    """
    Serializer para crear una venta con múltiples productos.
    La fecha se establece automáticamente con la hora exacta del servidor.
    """
    customer = serializers.IntegerField(help_text="ID del cliente")
    items = SaleItemSerializer(many=True, help_text="Lista de productos en el carrito")

    def get_transaction_label(self):
        return "venta"

    def get_entity_id(self, validated_data):
        return validated_data.get('customer')

    def execute_service(self, entity_id, user_id, items):
        return SaleService.create(entity_id, user_id, items)


class SaleDetailSerializer(InvoiceMovementsMixin, serializers.ModelSerializer):
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
