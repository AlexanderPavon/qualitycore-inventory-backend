# serializers/movement_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from inventory_app.models.movement import Movement
from inventory_app.models.product import Product
from inventory_app.services import MovementService
from inventory_app.constants import MovementType, ValidationMessages


def validate_movement_date(value):
    """
    Validación compartida para fecha de movimientos.
    - No puede ser futura
    - Solo se permiten movimientos del día actual
    """
    now = timezone.now()
    if value > now:
        raise serializers.ValidationError(
            "La fecha del movimiento no puede ser futura."
        )
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value < today_start:
        raise serializers.ValidationError(
            "Solo se pueden registrar movimientos del día actual. No se permiten fechas de días anteriores."
        )
    return value

class MovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    stock_before_movement = serializers.IntegerField(source='stock_in_movement', read_only=True)
    stock_after_movement = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source='product.supplier.name', read_only=True, default="")
    customer_name = serializers.CharField(source='customer.name', read_only=True, default="")
    user_name = serializers.CharField(source='user.name', read_only=True)
    corrected_by_id = serializers.IntegerField(source='corrected_by.id', read_only=True, default=None)
    correction_quantity = serializers.IntegerField(source='corrected_by.quantity', read_only=True, default=None)
    original_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Movement
        fields = [
            'id', 'movement_type', 'date', 'quantity', 'product', 'user',
            'product_name', 'stock_before_movement', 'stock_after_movement', 'supplier_name',
            'customer', 'customer_name', 'user_name', 'reason',
            'corrected_by_id', 'correction_quantity', 'original_quantity',
            'sale', 'purchase',
        ]
        read_only_fields = ['user']

    def get_stock_after_movement(self, obj):
        """
        Calcula el stock después del movimiento.
        stock_in_movement es el stock ANTES del movimiento.
        """
        stock_before = obj.stock_in_movement
        if obj.movement_type == MovementType.INPUT:
            return stock_before + obj.quantity
        elif obj.movement_type == MovementType.OUTPUT:
            return stock_before - obj.quantity
        elif obj.movement_type == MovementType.ADJUSTMENT:
            return stock_before + obj.quantity  # quantity con signo
        elif obj.movement_type == MovementType.CORRECTION:
            return stock_before + obj.quantity  # quantity con signo
        return stock_before

    def get_original_quantity(self, obj):
        """
        Para correcciones, retorna la cantidad del movimiento original.
        El original tiene corrected_by apuntando a esta corrección (relación inversa).
        """
        if obj.movement_type != MovementType.CORRECTION:
            return None
        original = obj.correction.first()
        return original.quantity if original else None

    def validate_date(self, value):
        return validate_movement_date(value)

    def create(self, validated_data):
        """
        Crea un movimiento delegando la lógica de negocio al servicio.
        El serializer solo se encarga de formatear/parsear datos.
        """
        movement_type = validated_data.get('movement_type')
        product = validated_data.get('product')
        quantity = validated_data.get('quantity')
        user = validated_data.get('user')
        customer = validated_data.get('customer')
        date = validated_data.get('date')

        try:
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


class CorrectionSerializer(serializers.Serializer):
    """
    Serializer para correcciones de movimientos existentes.
    Valida los datos antes de delegarlos al MovementService.
    """
    new_quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)

    def create(self, validated_data):
        user = validated_data['user']
        original_movement_id = validated_data['original_movement_id']
        request = validated_data.get('request')

        try:
            correction = MovementService.create_correction(
                original_movement_id=original_movement_id,
                new_quantity=validated_data['new_quantity'],
                reason=validated_data['reason'],
                user_id=user.id,
                request=request,
            )
            return correction
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                str(e.message) if hasattr(e, 'message') else str(e)
            )


class AdjustmentMovementSerializer(serializers.Serializer):
    """
    Serializer dedicado para ajustes de inventario.
    Separado del MovementSerializer para no acoplar el flujo de compra/venta
    con campos específicos de ajuste.
    """
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(deleted_at__isnull=True)
    )
    quantity = serializers.IntegerField()
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)
    date = serializers.DateTimeField(required=False)

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError(
                ValidationMessages.ADJUSTMENT_QUANTITY_NONZERO
            )
        return value

    def validate_date(self, value):
        return validate_movement_date(value)

    def create(self, validated_data):
        user = validated_data['user']
        request = validated_data.get('request')

        try:
            movement = MovementService.create_movement(
                movement_type=MovementType.ADJUSTMENT,
                product_id=validated_data['product'].id,
                quantity=validated_data['quantity'],
                user_id=user.id,
                date=validated_data.get('date'),
                reason=validated_data['reason'],
                request=request,
            )
            return movement
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
