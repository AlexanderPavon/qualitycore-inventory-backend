# views/list_mixins.py
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache


class IdempotentCreateMixin:
    """
    Mixin que añade soporte a Idempotency-Key en POST.

    Si el cliente envía el header Idempotency-Key y ya existe una respuesta
    cacheada para esa clave, la devuelve directamente sin volver a crear el
    recurso. Evita duplicados por reintentos de red.

    Atributos de clase que la subclase debe definir:
        idempotency_prefix (str): Prefijo para la clave de caché (ej. "sale").
        idempotency_ttl (int): Tiempo de vida en segundos (default 86400 = 24h).

    La subclase implementa _do_create() con la lógica específica de creación.

    Protocolo de claves en caché:
        idem:{prefix}:{key}       — respuesta cacheada (200 ya procesado)
        idem:{prefix}:{key}:lock  — mutex de 30s (petición en curso)

    Flujo:
        1. Si existe respuesta → 201 cached (reintento seguro).
        2. Si existe lock pero no respuesta → 409 (petición duplicada en curso).
        3. Si nada existe → adquiere lock atómicamente, procesa, cachea respuesta.

    El lock de 30s cubre el tiempo máximo razonable de procesamiento. Si el
    worker muere durante ese tiempo, el cliente puede reintentar pasados 30s.
    """
    idempotency_prefix: str = ""
    idempotency_ttl: int = 86400
    _LOCK_TTL: int = 30  # segundos

    def create(self, request, *args, **kwargs):
        idem_key = request.headers.get('Idempotency-Key')
        if not idem_key:
            return self._do_create(request, *args, **kwargs)

        cache_key = f'idem:{self.idempotency_prefix}:{idem_key}'
        lock_key = f'{cache_key}:lock'

        # Petición ya completada: devolver resultado cacheado
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_201_CREATED)

        # Intentar adquirir el lock de forma atómica (cache.add devuelve False
        # si la clave ya existe). Si otro worker ganó la carrera, 409.
        if not cache.add(lock_key, True, timeout=self._LOCK_TTL):
            return Response(
                {'detail': 'Petición duplicada en proceso. Reintenta en unos segundos.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            response = self._do_create(request, *args, **kwargs)
        finally:
            # Liberar el lock siempre, incluso si _do_create lanza excepción.
            # Si fue exitoso, la respuesta queda en cache_key; el lock ya no importa.
            cache.delete(lock_key)

        if response.status_code == status.HTTP_201_CREATED:
            cache.set(cache_key, response.data, timeout=self.idempotency_ttl)

        return response

    def _do_create(self, request, *args, **kwargs):
        """Subclases implementan aquí la lógica específica de creación."""
        raise NotImplementedError  # pragma: no cover


class NoPageMixin:
    """
    Mixin para vistas ListCreateAPIView que soportan el query param ?no_page=true.
    Cuando está presente, retorna todos los resultados sin paginar en formato
    estándar {count, next, previous, results} para compatibilidad con el cliente.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if request.query_params.get('no_page') == 'true':
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'count': len(serializer.data),  # datos ya en memoria — evita COUNT(*) extra
                'next': None,
                'previous': None,
                'results': serializer.data,
            })

        return super().list(request, *args, **kwargs)
