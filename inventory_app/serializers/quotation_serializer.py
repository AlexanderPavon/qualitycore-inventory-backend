# serializers/quotation_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from inventory_app.models.quotation import Quotation
from inventory_app.serializers.quoted_product_serializer import QuotedProductSerializer
from inventory_app.services import QuotationService
from inventory_app.utils.timezone_utils import to_local


class QuotationSerializer(serializers.ModelSerializer):
    quoted_products = QuotedProductSerializer(many=True)

    # Campos calculados por QuotationService — solo lectura en input
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    vat = serializers.DecimalField(source='tax', max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    observations = serializers.CharField(source='notes', required=False, allow_blank=True)

    # Convertir la fecha UTC a la zona horaria local configurada
    date = serializers.SerializerMethodField()

    def get_date(self, obj):
        """Convierte la fecha UTC a la zona horaria local"""
        local_date = to_local(obj.date)
        return local_date.isoformat() if local_date else None

    class Meta:
        model = Quotation
        fields = [
            'id', 'date', 'subtotal', 'vat', 'total',
            'observations', 'customer', 'user', 'quoted_products'
        ]

    def create(self, validated_data):
        """
        Crea una cotización delegando la lógica de negocio al servicio.
        El serializer solo se encarga de formatear/parsear datos.
        """
        # Extraer datos del request
        products_data = validated_data.pop('quoted_products')
        notes = validated_data.pop('notes', "")
        customer = validated_data.get('customer')
        user = validated_data.get('user')

        # Transformar productos al formato que espera el servicio
        products_for_service = [
            {
                'product_id': prod['product'].id,
                'quantity': prod['quantity'],
                'unit_price': prod['unit_price']
            }
            for prod in products_data
        ]

        try:
            # Delegar creación al servicio (lógica de negocio)
            quotation = QuotationService.create_quotation(
                customer_id=customer.id,
                user_id=user.id,
                products=products_for_service,
                notes=notes
            )
            return quotation

        except DjangoValidationError as e:
            # Convertir ValidationError de Django a DRF
            raise serializers.ValidationError(str(e))
