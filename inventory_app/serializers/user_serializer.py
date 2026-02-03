# serializers/user_serializer.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from inventory_app.models.user import User
from inventory_app.constants import UserRole

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'phone',
            'created_at', 'updated_at', 'password', 'is_active'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'phone': {
                'error_messages': {
                    'max_length': 'El teléfono no puede tener más de 15 caracteres.',
                    'blank': 'El teléfono no puede estar vacío.',
                    'required': 'El teléfono es requerido.',
                    'unique': 'Ya existe un usuario con este teléfono.'
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
                    'unique': 'Ya existe un usuario con este correo electrónico.'
                }
            }
        }

    def validate_password(self, value):
        """
        Valida que la contraseña cumpla con los requisitos de seguridad de Django
        """
        if value:
            try:
                # Validar con los validadores de Django configurados en settings
                validate_password(value)
            except DjangoValidationError as e:
                # Convertir los errores de Django a errores de DRF
                raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        """
        Valida que el email sea único en el sistema
        """
        # Normalizar el email a minúsculas
        value = value.lower()

        # Si estamos actualizando un usuario existente
        if self.instance:
            # Verificar si el email cambió
            if self.instance.email.lower() != value:
                # Verificar que no exista otro usuario con ese email
                if User.objects.filter(email__iexact=value, deleted_at__isnull=True).exists():
                    raise serializers.ValidationError("Ya existe un usuario con este correo electrónico.")
        else:
            # Si estamos creando un nuevo usuario
            if User.objects.filter(email__iexact=value, deleted_at__isnull=True).exists():
                raise serializers.ValidationError("Ya existe un usuario con este correo electrónico.")

        return value

    def validate_phone(self, value):
        """
        Valida que el teléfono sea único en el sistema
        """
        # Si estamos actualizando un usuario existente
        if self.instance:
            # Verificar si el teléfono cambió
            if self.instance.phone != value:
                # Verificar que no exista otro usuario con ese teléfono
                if User.objects.filter(phone=value, deleted_at__isnull=True).exists():
                    raise serializers.ValidationError("Ya existe un usuario con este teléfono.")
        else:
            # Si estamos creando un nuevo usuario
            if User.objects.filter(phone=value, deleted_at__isnull=True).exists():
                raise serializers.ValidationError("Ya existe un usuario con este teléfono.")

        return value

    def validate(self, attrs):
        """
        Validaciones adicionales para SuperAdmin
        """
        request = self.context.get('request')
        role = attrs.get('role')

        # Si se intenta crear/editar un SuperAdmin
        if role == UserRole.SUPER_ADMIN:
            # Solo un SuperAdmin puede crear otros SuperAdmin
            if request and request.user.role != UserRole.SUPER_ADMIN:
                raise serializers.ValidationError({
                    "role": "Solo un SuperAdmin puede asignar el rol de SuperAdmin."
                })

            # Limitar a máximo 2 SuperAdmins en el sistema
            superadmin_count = User.objects.filter(role=UserRole.SUPER_ADMIN, deleted_at__isnull=True).count()
            if self.instance is None:  # Creando nuevo usuario
                if superadmin_count >= 2:
                    raise serializers.ValidationError({
                        "role": "Ya existen 2 SuperAdmins en el sistema. No se pueden crear más."
                    })
            else:  # Editando usuario existente
                # Si estamos cambiando el rol a SuperAdmin
                if self.instance.role != UserRole.SUPER_ADMIN and superadmin_count >= 2:
                    raise serializers.ValidationError({
                        "role": "Ya existen 2 SuperAdmins en el sistema. No se pueden crear más."
                    })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            # La validación ya se hizo en validate_password()
            user.set_password(password)
        else:
            # Si no hay password, establecer uno temporal (el admin debería forzar cambio)
            raise serializers.ValidationError({"password": "La contraseña es requerida al crear un usuario."})
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            # La validación ya se hizo en validate_password()
            instance.set_password(password)
        instance.save()
        return instance

