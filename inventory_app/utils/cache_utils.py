# utils/cache_utils.py
"""
Utilidades de caché para optimizar consultas repetitivas.
Usa el sistema de caché de Django (puede ser in-memory o Redis).
"""
from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_queryset(timeout=300, key_prefix=''):
    """
    Decorador para cachear el resultado de una vista o método.

    Args:
        timeout: Tiempo en segundos que se guardará en caché (default: 5 minutos)
        key_prefix: Prefijo personalizado para la clave de caché

    Uso:
        @cache_queryset(timeout=3600, key_prefix='categories')
        def get_categories(request):
            return Category.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Crear una clave única basada en función y argumentos
            cache_key = _generate_cache_key(func.__name__, key_prefix, args, kwargs)

            # Intentar obtener del caché
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Si no está en caché, ejecutar función y guardar resultado
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        # Agregar método para invalidar caché
        wrapper.invalidate = lambda: cache.delete_pattern(f"{key_prefix or func.__name__}_*")
        return wrapper
    return decorator


def _generate_cache_key(func_name, prefix, args, kwargs):
    """
    Genera una clave de caché única basada en función y parámetros.
    """
    # Convertir args y kwargs a string determinístico
    args_str = str(args)
    kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
    combined = f"{args_str}_{kwargs_str}"

    # Hash para evitar claves muy largas
    hash_suffix = hashlib.md5(combined.encode()).hexdigest()[:8]

    cache_key = f"{prefix or func_name}_{hash_suffix}"
    return cache_key


def invalidate_cache(key_prefix):
    """
    Invalida (elimina) todas las entradas de caché con un prefijo específico.

    Uso:
        # Después de crear/actualizar/eliminar un producto
        invalidate_cache('products_list')
    """
    try:
        cache.delete_pattern(f"{key_prefix}_*")
    except AttributeError:
        # Si no tiene delete_pattern (caché simple), limpiar todo
        cache.clear()


class CacheInvalidator:
    """
    Context manager para invalidar caché al salir.

    Uso:
        with CacheInvalidator('products_list'):
            Product.objects.create(...)
        # Al salir del context, se invalida automáticamente
    """
    def __init__(self, *cache_keys):
        self.cache_keys = cache_keys

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key in self.cache_keys:
            invalidate_cache(key)
