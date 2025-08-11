# views/auth_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import BasePermission
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from inventory_app.models.user import User
from inventory_app.serializers.user_serializer import UserSerializer

# --- Login ---
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            if not user.is_active:
                return Response({'message': 'El usuario está inactivo. Contacta al administrador.'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            serializer = UserSerializer(user)
            return Response({'message': 'Inicio de sesión exitoso', 'user': serializer.data})
        return Response({'message': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)

# --- Forgot Password ---
class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = user.pk
            frontend_url = 'https://qualitycore-inventory-frontend-production.up.railway.app/reset-password'
            reset_url = f"{frontend_url}?uid={uid}&token={token}"
            send_mail(
                subject="Recupera tu contraseña",
                message=(
                    f"Hola,\n\n"
                    f"Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en QualityCore Services.\n\n"
                    f"Para crear una nueva contraseña, haz clic en el siguiente enlace o cópialo y pégalo en tu navegador:\n"
                    f"{reset_url}\n\n"
                    f"Si tú no solicitaste este cambio, puedes ignorar este correo y tu contraseña actual seguirá siendo válida. Si tienes alguna duda o detectas actividad sospechosa, por favor comunícate con la administradora.\n\n"
                    f"Gracias por confiar en nosotros.\n"
                    f"Equipo de QualityCore Services"
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response({'message': f"Se ha enviado un correo electrónico de recuperación de contraseña a {email}."})
        except User.DoesNotExist:
            return Response({'message': 'No se encontró un usuario con ese correo electrónico.'}, status=status.HTTP_400_BAD_REQUEST)

# --- Reset Password ---
class ResetPasswordView(APIView):
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        try:
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({'message': 'Contraseña actualizada correctamente'})
            else:
                return Response({'message': 'El token es inválido o ha expirado'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'message': 'Usuario no encontrado'}, status=status.HTTP_400_BAD_REQUEST)

# --- Admin Rol Check ---
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.rol == "Administrador"

# --- Change Password ---
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not user.check_password(old_password):
            return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Contraseña cambiada exitosamente'}, status=status.HTTP_200_OK)
