# serializers/quotation_serializer.py
from rest_framework import serializers
from inventory_app.models.quotation import Quotation
from inventory_app.serializers.quoted_product_serializer import QuotedProductSerializer
from inventory_app.models.quoted_product import QuotedProduct


class QuotationSerializer(serializers.ModelSerializer):
    quoted_products = QuotedProductSerializer(many=True)

    # Traducimos los nombres internos del modelo a nombres más amigables para el frontend
    vat = serializers.DecimalField(source='tax', max_digits=10, decimal_places=2)
    observations = serializers.CharField(source='notes', required=False, allow_blank=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'date', 'subtotal', 'vat', 'total',
            'observations', 'customer', 'user', 'quoted_products'
        ]

    def create(self, validated_data):
        # Sacamos los productos cotizados
        products_data = validated_data.pop('quoted_products')

        # Extraemos los campos renombrados
        tax = validated_data.pop('tax')
        notes = validated_data.pop('notes', "")

        # Creamos la cotización con los nombres del modelo
        quotation = Quotation.objects.create(**validated_data, tax=tax, notes=notes)

        # Creamos los productos cotizados vinculados
        for prod in products_data:
            QuotedProduct.objects.create(quotation=quotation, **prod)

        return quotation
