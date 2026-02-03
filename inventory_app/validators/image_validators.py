# validators/image_validators.py
"""
Validadores para imágenes de productos.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


def validate_image_size(image):
    """
    Valida que la imagen no exceda el tamaño máximo permitido (2 MB).
    """
    max_size_mb = 2
    max_size_bytes = max_size_mb * 1024 * 1024  # 2 MB en bytes

    if image.size > max_size_bytes:
        raise ValidationError(
            _(f"La imagen no puede exceder {max_size_mb} MB. Tamaño actual: {image.size / (1024 * 1024):.2f} MB."),
            code='image_too_large',
        )


def validate_image_dimensions(image):
    """
    Valida que la imagen tenga dimensiones razonables.
    Mínimo: 300x300 px
    Máximo: 2000x2000 px
    """
    from PIL import Image as PILImage

    img = PILImage.open(image)
    width, height = img.size

    min_dimension = 300
    max_dimension = 2000

    if width < min_dimension or height < min_dimension:
        raise ValidationError(
            _(f"La imagen debe tener al menos {min_dimension}x{min_dimension} píxeles. Tamaño actual: {width}x{height} px."),
            code='image_too_small',
        )

    if width > max_dimension or height > max_dimension:
        raise ValidationError(
            _(f"La imagen no puede exceder {max_dimension}x{max_dimension} píxeles. Tamaño actual: {width}x{height} px."),
            code='image_too_large_dimensions',
        )
