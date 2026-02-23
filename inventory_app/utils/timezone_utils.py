# utils/timezone_utils.py
"""
Utilidades centralizadas para manejo de timezone.
Usa settings.TIME_ZONE para todas las conversiones.
"""
from django.utils import timezone


def to_local(dt):
    """Convierte un datetime UTC a la zona horaria configurada en settings.TIME_ZONE."""
    if dt is None:
        return None
    return timezone.localtime(dt)


def local_now():
    """Retorna la fecha/hora actual en la zona horaria local (settings.TIME_ZONE)."""
    return timezone.localtime(timezone.now())
