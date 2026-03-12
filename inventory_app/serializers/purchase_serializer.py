# serializers/purchase_serializer.py
from rest_framework import serializers

from inventory_app.models.purchase import Purchase
from inventory_app.services import PurchaseService
from inventory_app.serializers.mixins import InvoiceMovementsMixin, TransactionSerializerMixin


class PurchaseItemSerializer(serializers.Serializer):
    """
    Serializer para cada producto en el carrito de una compra.
    """
    product = serializers.IntegerField(help_text="ID del producto")
    quantity = serializers.IntegerField(min_value=1, help_text="Cantidad a comprar")


class PurchaseCreateSerializer(TransactionSerializerMixin):
    """
    Serializer para crear una compra con múltiples productos.
    La fecha se establece automáticamente con la hora exacta del servidor.
    """
    supplier = serializers.IntegerField(help_text="ID del proveedor")
    items = PurchaseItemSerializer(many=True, help_text="Lista de productos en el carrito")

    def get_transaction_label(self):
        return "compra"

    def get_entity_id(self, validated_data):
        return validated_data.get('supplier')

    def execute_service(self, entity_id, user_id, items):
        return PurchaseService.create(entity_id, user_id, items)


class PurchaseDetailSerializer(InvoiceMovementsMixin, serializers.ModelSerializer):
    """
    Serializer para mostrar detalles de una compra.
    """
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    movements = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            'id', 'supplier', 'supplier_name', 'user', 'user_name',
            'date', 'total', 'movements', 'created_at'
        ]
