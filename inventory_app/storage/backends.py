# storage/backends.py
"""
Capa de abstracción de almacenamiento de imágenes.

Desacopla el serializer del proveedor concreto (Cloudinary, S3, local, etc.).
Para añadir un nuevo backend: implementar StorageBackend y registrarlo en
get_storage_backend() según la configuración de settings.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Interfaz para backends de almacenamiento de imágenes de productos."""

    @abstractmethod
    def get_image_url(self, image_field) -> Optional[str]:
        """
        Devuelve la URL pública de la imagen, o None si no está disponible.

        Args:
            image_field: Instancia de FieldFile (obj.image de un Product).

        Returns:
            URL pública como string, o None si la imagen no existe o no es pública.
        """


class CloudinaryBackend(StorageBackend):
    """Backend para imágenes alojadas en Cloudinary."""

    def get_image_url(self, image_field) -> Optional[str]:
        if not image_field:
            return None
        try:
            url = image_field.url
            if url and url.startswith('https://res.cloudinary.com/'):
                return url
            # URL pública genérica (ej. CDN custom sobre Cloudinary)
            if url and url.startswith('https://'):
                return url
            return None
        except Exception as exc:
            logger.error("CloudinaryBackend: error obteniendo URL de imagen: %s", exc)
            return None


class LocalStorageBackend(StorageBackend):
    """
    Backend para imágenes almacenadas localmente (/media/).

    Las rutas locales no son URLs públicas en producción, por lo que
    devuelve None. Útil para desarrollo sin Cloudinary configurado.
    """

    def get_image_url(self, image_field) -> Optional[str]:
        if not image_field:
            return None
        try:
            url = image_field.url
            # /media/ es accesible solo en dev (DEBUG=True + urls.py con static())
            if url and url.startswith('http'):
                return url
            return None
        except Exception as exc:
            logger.error("LocalStorageBackend: error obteniendo URL de imagen: %s", exc)
            return None


def get_storage_backend() -> StorageBackend:
    """
    Fábrica: devuelve el backend correcto según settings.USE_CLOUDINARY.

    Uso:
        from inventory_app.storage import get_storage_backend
        url = get_storage_backend().get_image_url(product.image)
    """
    from django.conf import settings
    if getattr(settings, 'USE_CLOUDINARY', False):
        return CloudinaryBackend()
    return LocalStorageBackend()
