# validators/image_validators.py
"""
Validadores para imágenes de productos.
Usa valores de ImageConfig en constants.py como fuente de verdad.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from inventory_app.constants import ImageConfig


def validate_image_size(image):
    """
    Valida que la imagen no exceda el tamaño máximo permitido.
    """
    if image.size > ImageConfig.MAX_SIZE_BYTES:
        raise ValidationError(
            _(f"La imagen no puede exceder {ImageConfig.MAX_SIZE_MB} MB. "
              f"Tamaño actual: {image.size / (1024 * 1024):.2f} MB."),
            code='image_too_large',
        )


def validate_image_dimensions(image):
    """
    Valida que la imagen tenga dimensiones razonables.
    """
    from PIL import Image as PILImage

    img = PILImage.open(image)
    width, height = img.size

    if width < ImageConfig.MIN_WIDTH or height < ImageConfig.MIN_HEIGHT:
        raise ValidationError(
            _(f"La imagen debe tener al menos {ImageConfig.MIN_WIDTH}x{ImageConfig.MIN_HEIGHT} píxeles. "
              f"Tamaño actual: {width}x{height} px."),
            code='image_too_small',
        )

    if width > ImageConfig.MAX_WIDTH or height > ImageConfig.MAX_HEIGHT:
        raise ValidationError(
            _(f"La imagen no puede exceder {ImageConfig.MAX_WIDTH}x{ImageConfig.MAX_HEIGHT} píxeles. "
              f"Tamaño actual: {width}x{height} px."),
            code='image_too_large_dimensions',
        )
