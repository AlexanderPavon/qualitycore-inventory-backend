# serializers/product_serializer.py
from rest_framework import serializers
from inventory_app.models.product import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
