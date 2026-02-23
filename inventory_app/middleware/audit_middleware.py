# middleware/audit_middleware.py
"""
Middleware para auditoría automática de todas las requests.
Registra información sobre quién accedió a qué y cuándo.
Expone el request actual via thread-local para que los signals puedan accederlo.
"""
import logging
import json
import threading
from django.utils import timezone

logger = logging.getLogger('inventory_app.audit')

# Thread-local storage para exponer el request a los signals
_thread_locals = threading.local()


def get_current_request():
    """Obtiene el request actual del thread-local (usado por signals)."""
    return getattr(_thread_locals, 'request', None)


class AuditMiddleware:
    """
    Middleware que registra todas las peticiones HTTP para crear un audit trail.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Guardar request en thread-local para que los signals puedan accederlo
        _thread_locals.request = request

        # Capturar datos de la request antes de procesarla (body, IP, method)
        request_body = self._capture_request_body(request)

        # Procesar la request (DRF autentica al usuario aquí)
        response = self.get_response(request)

        # Registrar request Y response (ahora el user ya está autenticado)
        self._log_request(request, request_body)
        self._log_response(request, response)

        # Limpiar thread-local
        _thread_locals.request = None

        return response

    def _capture_request_body(self, request):
        """Captura el body antes de que DRF lo consuma."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body) if request.body else None
                    if body and isinstance(body, dict):
                        return self._sanitize_data(body)
                    return body
            except (ValueError, TypeError):
                return "<binary or non-JSON data>"
        return None

    def _log_request(self, request, body=None):
        """Registra información de la request (se llama después de autenticación)."""
        user = getattr(request, 'user', None)
        user_info = 'Anonymous'

        if user and user.is_authenticated:
            user_info = f"{user.email} (ID: {user.id}, Role: {user.role})"

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
