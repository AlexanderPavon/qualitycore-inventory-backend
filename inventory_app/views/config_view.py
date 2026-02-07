# views/config_view.py
"""
Endpoint para exponer configuración del sistema al frontend.
Single source of truth para constantes compartidas.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from inventory_app.constants import BusinessRules, Timeouts, ImageConfig


class ConfigView(APIView):
    """
    GET /api/config/
    Retorna la configuración del sistema para el frontend.
    No requiere autenticación para permitir carga inicial.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        config = {
            # Tasas de impuestos
            'tax_rate': {
                'iva': BusinessRules.TAX_RATE,
            },

            # Paginación
            'pagination': {
                'default_page_size': BusinessRules.DEFAULT_PAGE_SIZE,
                'page_size_options': BusinessRules.PAGE_SIZE_OPTIONS,
            },

            # Validación
            'validation': {
                'phone_length': BusinessRules.MIN_PHONE_LENGTH,
                'password_min_length': BusinessRules.MIN_PASSWORD_LENGTH,
                'min_document_length': BusinessRules.MIN_DOCUMENT_LENGTH,
                'max_document_length': BusinessRules.MAX_DOCUMENT_LENGTH,
            },

            # Timeouts (en milisegundos)
            'timeouts': {
                'toast_default': Timeouts.TOAST_DEFAULT,
                'toast_short': Timeouts.TOAST_SHORT,
                'toast_long': Timeouts.TOAST_LONG,
                'message_display': Timeouts.MESSAGE_DISPLAY,
                'redirect_delay': Timeouts.REDIRECT_DELAY,
                'polling_interval': Timeouts.POLLING_INTERVAL,
                'clock_interval': Timeouts.CLOCK_INTERVAL,
            },

            # Configuración de imágenes
            'image': {
                'max_size_mb': ImageConfig.MAX_SIZE_MB,
                'max_size_bytes': ImageConfig.MAX_SIZE_BYTES,
                'min_width': ImageConfig.MIN_WIDTH,
                'min_height': ImageConfig.MIN_HEIGHT,
                'max_width': ImageConfig.MAX_WIDTH,
                'max_height': ImageConfig.MAX_HEIGHT,
                'allowed_types': ImageConfig.ALLOWED_TYPES,
                'allowed_extensions': ImageConfig.ALLOWED_EXTENSIONS,
            },

            # Límites de negocio
            'limits': {
                'max_product_price': float(BusinessRules.MAX_PRODUCT_PRICE),
                'max_quantity': BusinessRules.MAX_QUANTITY,
            },
        }

        return Response(config)
