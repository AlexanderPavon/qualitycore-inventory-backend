# views/user_view.py
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from inventory_app.serializers.user_serializer import UserSerializer
from inventory_app.constants import UserRole
from inventory_app.permissions import IsAdmin
from inventory_app.throttles import WriteOperationThrottle

User = get_user_model()

# --- User CRUD ---
class UserListCreateView(generics.ListCreateAPIView):
    # Excluir usuarios soft-deleted (deleted_at != null)
    queryset = User.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    throttle_classes = [WriteOperationThrottle]

    def perform_create(self, serializer):
        # Solo SuperAdmin puede crear usuarios
        if self.request.user.role != UserRole.SUPER_ADMIN:
            raise PermissionDenied("Solo un SuperAdmin puede crear nuevos usuarios.")
        serializer.save()

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    throttle_classes = [WriteOperationThrottle]

    def perform_update(self, serializer):
        """
        Validaciones adicionales antes de actualizar usuario
        """
        target_user = self.get_object()
        current_user = self.request.user
        new_is_active = serializer.validated_data.get('is_active', target_user.is_active)

        # REGLA 1: Nadie puede inactivarse a sí mismo
        if target_user.id == current_user.id and new_is_active == False:
            raise PermissionDenied("No puedes inactivarte a ti mismo.")

        # REGLA 2: Solo SuperAdmin puede inactivar a otros Admins o SuperAdmins
        if target_user.role in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN]:
            if current_user.role != UserRole.SUPER_ADMIN:
                raise PermissionDenied("Solo un SuperAdmin puede modificar a otros Administradores o SuperAdmins.")

        # REGLA 3: SuperAdmin no puede ser inactivado (protección extra)
        if target_user.role == UserRole.SUPER_ADMIN and new_is_active == False:
            # Verificar que haya al menos 1 SuperAdmin activo restante
            active_superadmins = User.objects.filter(
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                deleted_at__isnull=True
            ).exclude(id=target_user.id).count()

            if active_superadmins == 0:
                raise PermissionDenied("No se puede inactivar al único SuperAdmin activo del sistema.")

        serializer.save()

