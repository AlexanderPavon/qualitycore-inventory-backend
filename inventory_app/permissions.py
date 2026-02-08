# permissions.py
"""
Clases de permisos reutilizables para todas las vistas del sistema.
Centraliza la lógica de autorización basada en roles.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from inventory_app.constants import UserRole


class IsSuperAdmin(BasePermission):
    """Solo permite acceso a SuperAdmin."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )


class IsAdmin(BasePermission):
    """Permite acceso a Administrator y SuperAdmin."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN]
        )


class IsAdminForWrite(BasePermission):
    """
    Lectura (GET, HEAD, OPTIONS): cualquier usuario autenticado.
    Escritura (POST, PUT, PATCH, DELETE): solo Admin o SuperAdmin.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN]
