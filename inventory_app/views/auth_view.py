# views/auth_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import BasePermission
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from inventory_app.models.user import User
from inventory_app.serializers.user_serializer import UserSerializer
from inventory_app.throttles import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    PasswordChangeRateThrottle,
)

# --- Login ---
class LoginView(APIView):
    throttle_classes = [LoginRateThrottle]

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
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = user.pk

            # Obtener URL del frontend desde variables de entorno
            # Permite desarrollo local y producción sin cambiar código
            frontend_base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_base_url}/reset-password?uid={uid}&token={token}"
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
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        # Validar que se proporcionó la contraseña
        if not new_password:
            return Response({'message': 'La nueva contraseña es requerida'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                # Validar la nueva contraseña con los validadores de Django
                try:
                    validate_password(new_password, user=user)
                except ValidationError as e:
                    return Response({'message': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)
                user.save()
                return Response({'message': 'Contraseña actualizada correctamente'})
            else:
                return Response({'message': 'El token es inválido o ha expirado'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'message': 'Usuario no encontrado'}, status=status.HTTP_400_BAD_REQUEST)

# --- Change Password ---
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PasswordChangeRateThrottle]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # Validar que se proporcionaron ambas contraseñas
        if not old_password:
            return Response({'error': 'La contraseña actual es requerida.'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'La nueva contraseña es requerida.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar la contraseña actual
        if not user.check_password(old_password):
            return Response({'error': 'La contraseña actual es incorrecta.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validar la nueva contraseña con los validadores de Django
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({'error': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Contraseña cambiada exitosamente'}, status=status.HTTP_200_OK)
