# views/token_refresh_view.py
"""
Vista de refresh de JWT que lee el refresh token de una cookie httpOnly
y escribe los nuevos tokens como cookies httpOnly.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings


class CookieTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token_str = request.COOKIES.get("refresh_token")
        if not refresh_token_str:
            return Response(
                {'detail': 'No se encontró el refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token_str)
            new_access_token = str(refresh.access_token)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        is_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        same_site = getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')
        access_max_age = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
        refresh_max_age = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())

        response = Response({'message': 'Token renovado'})

        response.set_cookie(
            key="access_token",
            value=new_access_token,
            max_age=access_max_age,
            httponly=True,
            secure=is_secure,
            samesite=same_site,
            path="/",
        )

        # Rotar refresh token (ROTATE_REFRESH_TOKENS=True)
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            max_age=refresh_max_age,
            httponly=True,
            secure=is_secure,
            samesite=same_site,
            path="/api/token/refresh/",
        )

        return response
