# serializers/movement_serializer.py
from rest_framework import serializers
from inventory_app.models.movement import Movement

class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_stock = serializers.IntegerField(source='stock_in_movement', read_only=True)
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True, default="")
    customer_name = serializers.CharField(source='customer.name', read_only=True, default="")
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Movement
        fields = [
            'id', 'movement_type', 'date', 'quantity', 'product',
            'product_name', 'product_stock', 'supplier_name',
            'customer', 'customer_name', 'user_name'
        ]
