# authentication.py
"""
Autenticación JWT basada en cookies httpOnly.
Lee el access token de la cookie en vez del header Authorization.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    Lee el access token de la cookie 'access_token' httpOnly.
    Retorna None si no hay cookie (permite endpoints públicos).
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return self.get_user(validated_token), validated_token
