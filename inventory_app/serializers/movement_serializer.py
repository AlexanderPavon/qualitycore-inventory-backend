# serializers/movement_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from inventory_app.models.movement import Movement
from inventory_app.services import MovementService

class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_stock = serializers.IntegerField(source='stock_in_movement', read_only=True)
    stock_after_movement = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True, default="")
    customer_name = serializers.CharField(source='customer.name', read_only=True, default="")
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Movement
        fields = [
            'id', 'movement_type', 'date', 'quantity', 'product', 'user',
            'product_name', 'product_stock', 'stock_after_movement', 'supplier_name',
            'customer', 'customer_name', 'user_name'
        ]

    def get_stock_after_movement(self, obj):
        """
        Calcula el stock después del movimiento.
        stock_in_movement es el stock ANTES del movimiento.
        """
        from inventory_app.constants import MovementType

        stock_before = obj.stock_in_movement
        if obj.movement_type == MovementType.INPUT:
            return stock_before + obj.quantity
        elif obj.movement_type == MovementType.OUTPUT:
            return stock_before - obj.quantity
        return stock_before

    def validate_date(self, value):
        """
        Valida que la fecha del movimiento sea válida:
        - Solo se permiten movimientos del día actual
        - No puede ser futura
        - No puede ser de días anteriores
        """
        now = timezone.now()

        # Validar que no sea una fecha futura
        if value > now:
            raise serializers.ValidationError(
                "La fecha del movimiento no puede ser futura."
            )

        # Validar que sea del día actual (mismo día)
        # Obtener el inicio del día actual (00:00:00)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if value < today_start:
            raise serializers.ValidationError(
                "Solo se pueden registrar movimientos del día actual. No se permiten fechas de días anteriores."
            )

        return value

    def create(self, validated_data):
        """
        Crea un movimiento delegando la lógica de negocio al servicio.
        El serializer solo se encarga de formatear/parsear datos.
        """
        # Extraer datos del request
        movement_type = validated_data.get('movement_type')
        product = validated_data.get('product')
        quantity = validated_data.get('quantity')
        user = validated_data.get('user')
        customer = validated_data.get('customer')
        date = validated_data.get('date')

        try:
            # Delegar creación al servicio (lógica de negocio)
            movement = MovementService.create_movement(
                movement_type=movement_type,
                product_id=product.id,
                quantity=quantity,
                user_id=user.id,
                customer_id=customer.id if customer else None,
                date=date
            )
            return movement

        except DjangoValidationError as e:
            # Convertir ValidationError de Django a DRF
            raise serializers.ValidationError(str(e))
