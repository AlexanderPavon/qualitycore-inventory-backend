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
                return Response({'message': 'Inactive user. Contact admin.'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            serializer = UserSerializer(user)
            return Response({'message': 'Login successful', 'user': serializer.data})
        return Response({'message': 'Incorrect credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# --- Forgot Password ---
class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = user.pk
            frontend_url = 'http://localhost:3000/reset-password'
            reset_url = f"{frontend_url}?uid={uid}&token={token}"

            send_mail(
                subject="Reset your password",
                message=(
                    f"Hi,\n\nWe received a request to reset your password.\n"
                    f"Link: {reset_url}\n\n"
                    f"If you didn't request this, ignore this message."
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response({'message': f"A password recovery email has been sent to {email}."})
        except User.DoesNotExist:
            return Response({'message': 'No user with that email found.'}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({'message': 'Password successfully updated'})
            else:
                return Response({'message': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

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
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
