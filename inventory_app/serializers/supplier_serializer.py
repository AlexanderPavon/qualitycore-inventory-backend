# serializers/supplier_serializer.py
from rest_framework import serializers
from inventory_app.models.supplier import Supplier

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'