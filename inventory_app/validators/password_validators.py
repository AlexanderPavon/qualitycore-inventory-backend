# validators/password_validators.py
"""
Validadores para contraseñas de usuarios.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexPasswordValidator:
    """
    Valida que la contraseña contenga:
    - Al menos una letra mayúscula
    - Al menos una letra minúscula
    - Al menos un número
    - Al menos un carácter especial
    - Mínimo 8 caracteres
    """

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(
                _("La contraseña debe tener al menos 8 caracteres."),
                code='password_too_short',
            )

        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos una letra mayúscula."),
                code='password_no_upper',
            )

        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos una letra minúscula."),
                code='password_no_lower',
            )

        if not re.search(r'\d', password):
            raise ValidationError(
                _("La contraseña debe contener al menos un número."),
                code='password_no_digit',
            )

        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;~`]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos un carácter especial (!@#$%^&*(),.?\":{}|<>_-+=[]\\\/;~`)."),
                code='password_no_special',
            )

    def get_help_text(self):
        return _(
            "Tu contraseña debe contener al menos 8 caracteres, incluyendo una letra mayúscula, "
            "una letra minúscula, un número y un carácter especial (!@#$%^&*(),.?\":{}|<>_-+=[]\\\/;~`)."
        )
