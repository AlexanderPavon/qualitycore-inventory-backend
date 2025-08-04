# serializers/customer_serializer.py
from rest_framework import serializers
from inventory_app.models.customer import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'