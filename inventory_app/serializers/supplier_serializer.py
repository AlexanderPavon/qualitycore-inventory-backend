# serializers/supplier_serializer.py
from rest_framework import serializers
from inventory_app.models.supplier import Supplier
from inventory_app.validators.ecuadorian_validators import (
    validate_ecuadorian_cedula,
    validate_ecuadorian_ruc,
    validate_passport
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required': 'El nombre es requerido.',
                    'blank': 'El nombre no puede estar vacío.',
                    'max_length': 'El nombre no puede tener más de 100 caracteres.'
                }
            },
            'email': {
                'error_messages': {
                    'required': 'El correo es requerido.',
                    'blank': 'El correo no puede estar vacío.',
                    'invalid': 'Ingrese un correo electrónico válido.',
                    'max_length': 'El correo no puede tener más de 100 caracteres.',
                    'unique': 'Ya existe un proveedor con este correo electrónico.'
                }
            },
            'document_type': {
                'error_messages': {
                    'required': 'El tipo de documento es requerido.',
                    'invalid_choice': 'Tipo de documento inválido. Debe ser: cedula, ruc o passport.'
                }
            },
            'tax_id': {
                'error_messages': {
                    'required': 'El documento es requerido.',
                    'blank': 'El documento no puede estar vacío.',
                    'max_length': 'El documento no puede tener más de 13 caracteres.',
                    'unique': 'Ya existe un proveedor con este documento.'
                }
            },
            'phone': {
                'error_messages': {
                    'required': 'El teléfono es requerido.',
                    'blank': 'El teléfono no puede estar vacío.',
                    'max_length': 'El teléfono no puede tener más de 15 caracteres.',
                    'unique': 'Ya existe un proveedor con este teléfono.'
                }
            },
            'address': {
                'error_messages': {
                    'max_length': 'La dirección no puede tener más de 255 caracteres.'
                }
            }
        }

    def _check_unique(self, field, value, error_msg):
        """Verifica unicidad solo entre registros activos (no eliminados)."""
        qs = Supplier.objects.filter(**{field: value}, deleted_at__isnull=True)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(error_msg)

    def validate_email(self, value):
        self._check_unique('email', value.lower(), 'Ya existe un proveedor con este correo electrónico.')
        return value.lower()

    def validate_tax_id(self, value):
        self._check_unique('tax_id', value, 'Ya existe un proveedor con este documento.')
        return value

    def validate_phone(self, value):
        self._check_unique('phone', value, 'Ya existe un proveedor con este teléfono.')
        return value

    def validate(self, data):
        """
        Validación a nivel de objeto para verificar el documento según el tipo.
        """
        document_type = data.get('document_type')
        tax_id = data.get('tax_id')

        # Si estamos actualizando y no se proporciona document_type, usar el existente
        if not document_type and self.instance:
            document_type = self.instance.document_type

        # Si estamos actualizando y no se proporciona tax_id, usar el existente
        if not tax_id and self.instance:
            tax_id = self.instance.tax_id

        if document_type and tax_id:
            # Validar según el tipo de documento
            if document_type == 'cedula':
                validate_ecuadorian_cedula(tax_id)
            elif document_type == 'ruc':
                validate_ecuadorian_ruc(tax_id)
            elif document_type == 'passport':
                validate_passport(tax_id)

        return data
