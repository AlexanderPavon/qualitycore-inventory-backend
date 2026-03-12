# services/user_service.py
"""
Lógica de negocio para gestión de usuarios.
Centraliza las reglas de autorización para que sean aplicables desde
cualquier punto de entrada (views, management commands, tests, etc.).
"""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied

from inventory_app.constants import UserRole

User = get_user_model()


class UserService:
    """
    Servicio de negocio para operaciones sobre usuarios.

    Las reglas de autorización viven aquí, no en las vistas, para que
    sean reutilizables desde cualquier punto de entrada al sistema.
    """

    @staticmethod
    def validate_update_permissions(target_user, requesting_user, new_is_active: bool) -> None:
        """
        Valida las reglas de negocio antes de actualizar un usuario.

        Reglas:
        1. Nadie puede inactivarse a sí mismo.
        2. Solo SuperAdmin puede modificar Administradores u otros SuperAdmins.
        3. No se puede inactivar al único SuperAdmin activo del sistema.

        Args:
            target_user:      Usuario que se va a modificar.
            requesting_user:  Usuario autenticado que hace la petición.
            new_is_active:    Valor de is_active que se quiere establecer.

        Raises:
            PermissionDenied: si alguna regla es violada.
        """
        # REGLA 1: Nadie puede inactivarse a sí mismo
        if target_user.id == requesting_user.id and not new_is_active:
            raise PermissionDenied("No puedes inactivarte a ti mismo.")

        # REGLA 2: Solo SuperAdmin puede modificar Admins o SuperAdmins
        if target_user.role in (UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN):
            if requesting_user.role != UserRole.SUPER_ADMIN:
                raise PermissionDenied(
                    "Solo un SuperAdmin puede modificar a otros Administradores o SuperAdmins."
                )

        # REGLA 3: No se puede inactivar al único SuperAdmin activo
        if target_user.role == UserRole.SUPER_ADMIN and not new_is_active:
            remaining = User.objects.filter(
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                deleted_at__isnull=True,
            ).exclude(id=target_user.id).count()

            if remaining == 0:
                raise PermissionDenied(
                    "No se puede inactivar al único SuperAdmin activo del sistema."
                )
