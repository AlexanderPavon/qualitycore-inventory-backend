# views/user_view.py
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from inventory_app.serializers.user_serializer import UserSerializer

User = get_user_model()

# --- Custom Permission for Admin ---
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "Administrator"

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
        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


# --- Forgot Password ---
class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = user.pk
            frontend_url = 'https://qualitycore-inventory-frontend-r1a81m58r.vercel.app/reset-password'
            reset_url = f"{frontend_url}?uid={uid}&token={token}"

            send_mail(
                subject="Reset your password",
                message=(
                    f"Hi,\n\nYou requested to reset your password.\n"
                    f"Click the link: {reset_url}\n\n"
                    f"If you didn't request this, ignore this message."
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response({'message': f'Email sent to {email} for password reset.'})
        except User.DoesNotExist:
            return Response({'message': 'No user with that email.'}, status=status.HTTP_400_BAD_REQUEST)


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
                return Response({'message': 'Password changed successfully'})
            else:
                return Response({'message': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


# --- Change Password ---
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not user.check_password(old_password):
            return Response({'error': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'})


# --- User CRUD ---
class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        serializer.save()

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

