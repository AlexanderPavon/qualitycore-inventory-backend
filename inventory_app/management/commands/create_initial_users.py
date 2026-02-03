"""
Comando de Django para crear usuarios iniciales de forma segura.

Uso:
    python manage.py create_initial_users

Configuración:
    Define las credenciales en variables de entorno:
    - ADMIN_EMAIL_1 (requerido)
    - ADMIN_PASSWORD_1 (requerido)
    - ADMIN_NAME_1 (requerido)
    - ADMIN_PHONE_1 (requerido)
    - ADMIN_EMAIL_2 (opcional)
    - ADMIN_PASSWORD_2 (opcional)
    - ADMIN_NAME_2 (opcional)
    - ADMIN_PHONE_2 (opcional)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from inventory_app.constants import UserRole
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea usuarios administradores iniciales desde variables de entorno'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la creación de usuarios incluso si ya existen',
        )

    def handle(self, *args, **options):
        """
        Crea usuarios administradores desde variables de entorno.
        """
        force = options.get('force', False)

        # Lista de usuarios a crear (puedes agregar más)
        users_config = [
            {
                'email': os.environ.get('ADMIN_EMAIL_1'),
                'password': os.environ.get('ADMIN_PASSWORD_1'),
                'name': os.environ.get('ADMIN_NAME_1'),
                'phone': os.environ.get('ADMIN_PHONE_1'),
            },
            {
                'email': os.environ.get('ADMIN_EMAIL_2'),
                'password': os.environ.get('ADMIN_PASSWORD_2'),
                'name': os.environ.get('ADMIN_NAME_2'),
                'phone': os.environ.get('ADMIN_PHONE_2'),
            },
        ]

        created_count = 0
        skipped_count = 0
        error_count = 0

        for user_data in users_config:
            email = user_data.get('email')
            password = user_data.get('password')
            name = user_data.get('name')
            phone = user_data.get('phone')

            # Skip si no hay email (significa que no se configuró)
            if not email:
                continue

            # Validar que todos los campos estén presentes
            if not password or not name or not phone:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Saltando {email}: Faltan credenciales (password, name o phone)'
                    )
                )
                error_count += 1
                continue

            # Verificar si el usuario ya existe
            if User.objects.filter(email=email).exists():
                if force:
                    user = User.objects.get(email=email)
                    user.set_password(password)
                    user.name = name
                    user.phone = phone
                    user.role = UserRole.SUPER_ADMIN
                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Usuario actualizado: {email}')
                    )
                    created_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⏭️  Usuario ya existe: {email} (usa --force para actualizar)')
                    )
                    skipped_count += 1
                continue

            # Crear el superusuario
            try:
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    name=name,
                    phone=phone,
                    role=UserRole.SUPER_ADMIN
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Superusuario creado: {email}')
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creando {email}: {str(e)}')
                )
                error_count += 1

        # Resumen final
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'✅ Creados/Actualizados: {created_count}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Saltados: {skipped_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores: {error_count}'))
        self.stdout.write('=' * 60)

        if created_count == 0 and skipped_count == 0 and error_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  No se configuraron usuarios. '
                    'Define las variables de entorno ADMIN_EMAIL_1, ADMIN_PASSWORD_1, ADMIN_NAME_1, ADMIN_PHONE_1'
                )
            )
