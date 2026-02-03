# serializers/customer_serializer.py
from rest_framework import serializers
from inventory_app.models.customer import Customer
from inventory_app.validators.ecuadorian_validators import (
    validate_ecuadorian_cedula,
    validate_ecuadorian_ruc,
    validate_passport
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        extra_kwargs = {
            'phone': {
                'error_messages': {
                    'max_length': 'El teléfono no puede tener más de 15 caracteres.',
                    'required': 'El teléfono es requerido.',
                    'blank': 'El teléfono no puede estar vacío.',
                    'unique': 'Ya existe un cliente con este teléfono.'
                }
            },
            'document': {
                'error_messages': {
                    'required': 'El documento es requerido.',
                    'blank': 'El documento no puede estar vacío.',
                    'unique': 'Ya existe un cliente con este documento.'
                }
            },
            'document_type': {
                'error_messages': {
                    'required': 'El tipo de documento es requerido.',
                    'invalid_choice': 'Tipo de documento inválido. Debe ser: cedula, ruc o passport.'
                }
            },
            'name': {
                'error_messages': {
                    'required': 'El nombre es requerido.',
                    'blank': 'El nombre no puede estar vacío.'
                }
            },
            'email': {
                'error_messages': {
                    'invalid': 'Ingrese un correo electrónico válido.',
                    'required': 'El correo es requerido.',
                    'blank': 'El correo no puede estar vacío.',
                    'unique': 'Ya existe un cliente con este correo electrónico.'
                }
            },
            'address': {
                'error_messages': {
                    'required': 'La dirección es requerida.',
                    'blank': 'La dirección no puede estar vacía.'
                }
            }
        }

    def validate(self, data):
        """
        Validación a nivel de objeto para verificar el documento según el tipo.
        """
        document_type = data.get('document_type')
        document = data.get('document')

        # Si estamos actualizando y no se proporciona document_type, usar el existente
        if not document_type and self.instance:
            document_type = self.instance.document_type

        # Si estamos actualizando y no se proporciona document, usar el existente
        if not document and self.instance:
            document = self.instance.document

        if document_type and document:
            # Validar según el tipo de documento
            if document_type == 'cedula':
                validate_ecuadorian_cedula(document)
            elif document_type == 'ruc':
                validate_ecuadorian_ruc(document)
            elif document_type == 'passport':
                validate_passport(document)

        return data
