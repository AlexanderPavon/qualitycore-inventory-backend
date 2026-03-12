# serializers/user_serializer.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from inventory_app.models.user import User
from inventory_app.constants import UserRole, BusinessRules

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

            # Verificación rápida (sin lock) para feedback inmediato al usuario.
            # La validación definitiva con SELECT FOR UPDATE ocurre en create()/update()
            # dentro de transaction.atomic(), donde el lock tiene sentido y no lanza
            # TransactionManagementError en PostgreSQL (ATOMIC_REQUESTS no está activo).
            max_sa = BusinessRules.MAX_SUPERADMINS
            superadmin_count = (
                User.objects
                .filter(role=UserRole.SUPER_ADMIN, deleted_at__isnull=True)
                .count()
            )
            if self.instance is None:  # Creando nuevo usuario
                if superadmin_count >= max_sa:
                    raise serializers.ValidationError({
                        "role": f"Ya existen {max_sa} SuperAdmins en el sistema. No se pueden crear más."
                    })
            else:  # Editando usuario existente
                # Si estamos cambiando el rol a SuperAdmin
                if self.instance.role != UserRole.SUPER_ADMIN and superadmin_count >= max_sa:
                    raise serializers.ValidationError({
                        "role": f"Ya existen {max_sa} SuperAdmins en el sistema. No se pueden crear más."
                    })

        return attrs

    def _check_superadmin_limit_locked(self, adding_new_superadmin: bool) -> None:
        """
        Verificación definitiva del límite de SuperAdmins con SELECT FOR UPDATE.
        Debe llamarse desde dentro de un bloque transaction.atomic().
        Si adding_new_superadmin es False, es un no-op.
        """
        if not adding_new_superadmin:
            return
        max_sa = BusinessRules.MAX_SUPERADMINS
        superadmin_count = (
            User.objects
            .filter(role=UserRole.SUPER_ADMIN, deleted_at__isnull=True)
            .select_for_update()
            .count()
        )
        if superadmin_count >= max_sa:
            raise serializers.ValidationError({
                "role": f"Ya existen {max_sa} SuperAdmins en el sistema. No se pueden crear más."
            })

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "La contraseña es requerida al crear un usuario."})
        new_role = validated_data.get('role', '')
        with transaction.atomic():
            # Verificación definitiva con lock: previene race condition donde dos requests
            # simultáneos crearían ambos un SuperAdmin extra pasando el check por separado.
            self._check_superadmin_limit_locked(
                adding_new_superadmin=(new_role == UserRole.SUPER_ADMIN)
            )
            user = User(**validated_data)
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        old_role = instance.role
        new_role = validated_data.get('role', old_role)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        with transaction.atomic():
            self._check_superadmin_limit_locked(
                adding_new_superadmin=(
                    new_role == UserRole.SUPER_ADMIN and old_role != UserRole.SUPER_ADMIN
                )
            )
            instance.save()
        return instance

