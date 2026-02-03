# middleware/audit_middleware.py
"""
Middleware para auditoría automática de todas las requests.
Registra información sobre quién accedió a qué y cuándo.
"""
import logging
import json
from django.utils import timezone

logger = logging.getLogger('inventory_app.audit')


class AuditMiddleware:
    """
    Middleware que registra todas las peticiones HTTP para crear un audit trail.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Registrar la request antes de procesarla
        self._log_request(request)

        # Procesar la request
        response = self.get_response(request)

        # Registrar la response
        self._log_response(request, response)

        return response

    def _log_request(self, request):
        """Registra información de la request entrante"""
        user = getattr(request, 'user', None)
        user_info = 'Anonymous'

        if user and user.is_authenticated:
            user_info = f"{user.email} (ID: {user.id}, Role: {user.role})"

        # Obtener el cuerpo de la request para requests POST/PUT/PATCH
        body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body) if request.body else None
                    # Ocultar campos sensibles
                    if body and isinstance(body, dict):
                        body = self._sanitize_data(body)
            except:
                body = "<binary or non-JSON data>"

        logger.info(
            f"[REQUEST] {request.method} {request.path} | "
            f"User: {user_info} | "
            f"IP: {self._get_client_ip(request)} | "
            f"Body: {body}"
        )

    def _log_response(self, request, response):
        """Registra información de la response"""
        user = getattr(request, 'user', None)
        user_info = 'Anonymous'

        if user and user.is_authenticated:
            user_info = f"{user.email}"

        logger.info(
            f"[RESPONSE] {request.method} {request.path} | "
            f"Status: {response.status_code} | "
            f"User: {user_info}"
        )

    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _sanitize_data(self, data):
        """
        Remueve o enmascara campos sensibles del log.
        """
        sensitive_fields = ['password', 'token', 'secret', 'api_key', 'authorization']
        sanitized = data.copy()

        for key in list(sanitized.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = '***REDACTED***'

        return sanitized
