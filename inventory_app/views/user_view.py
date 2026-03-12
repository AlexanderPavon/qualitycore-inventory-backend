# views/user_view.py
from rest_framework import generics, status, permissions
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from inventory_app.serializers.user_serializer import UserSerializer
from inventory_app.constants import UserRole
from inventory_app.permissions import IsAdmin, IsSuperAdmin
from inventory_app.throttles import WriteThrottleMixin
from inventory_app.services.user_service import UserService

User = get_user_model()

# --- Sesión activa ---
class UserMeView(generics.RetrieveAPIView):
    """Retorna el usuario autenticado actual. Usado por el frontend para validar sesión al arrancar."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# --- User CRUD ---
class UserListCreateView(WriteThrottleMixin, generics.ListCreateAPIView):
    # Excluir usuarios soft-deleted (deleted_at != null)
    queryset = User.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = UserSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['name', 'id']
    ordering = ['-id']

    def get_permissions(self):
        # GET (listar): cualquier Admin o SuperAdmin puede ver la lista.
        # POST (crear): solo SuperAdmin puede crear usuarios.
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [IsAdmin()]

class UserDetailView(WriteThrottleMixin, generics.RetrieveUpdateAPIView):
    queryset = User.objects.filter(deleted_at__isnull=True)
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def perform_update(self, serializer):
        target_user = self.get_object()
        new_is_active = serializer.validated_data.get('is_active', target_user.is_active)
        UserService.validate_update_permissions(target_user, self.request.user, new_is_active)
        serializer.save()

