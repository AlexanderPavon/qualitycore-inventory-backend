# views/health_view.py
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])  # Sin rate limiting para health checks
def health_check(request):
    """
    Health check endpoint para orquestadores (Railway, Docker, K8s).
    Verifica conexión a BD y Redis/cache.
    """
    checks = {}

    # Verificar base de datos
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        logger.error(f"Health check: DB failed - {e}")
        checks['database'] = 'error'

    # Verificar cache (Redis)
    try:
        cache.set('health_check', 'ok', timeout=5)
        value = cache.get('health_check')
        checks['cache'] = 'ok' if value == 'ok' else 'error'
    except Exception as e:
        logger.error(f"Health check: Cache failed - {e}")
        checks['cache'] = 'error'

    all_ok = all(v == 'ok' for v in checks.values())

    return Response(
        {'status': 'healthy' if all_ok else 'unhealthy', 'checks': checks},
        status=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
