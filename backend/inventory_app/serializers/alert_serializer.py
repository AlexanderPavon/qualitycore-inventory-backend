# serializers/alert_serializer.py
from rest_framework import serializers
from inventory_app.models.alert import Alert

class AlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Alert
        fields = ['id', 'type', 'type_display', 'message', 'product_name', 'created_at']
