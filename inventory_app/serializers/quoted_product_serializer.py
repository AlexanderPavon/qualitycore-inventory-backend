# serializers/quoted_product_serializer.py
from rest_framework import serializers
from inventory_app.models.quoted_product import QuotedProduct

class QuotedProductSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = QuotedProduct
        fields = ['product', 'quantity', 'unit_price', 'subtotal']

