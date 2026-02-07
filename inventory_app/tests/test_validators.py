# tests/test_validators.py
"""
Tests para validadores del sistema.
Cubre: cédula ecuatoriana, RUC, pasaporte, contraseña, teléfono, precios y cantidades.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from inventory_app.validators.ecuadorian_validators import (
    validate_ecuadorian_cedula,
    validate_ecuadorian_ruc,
    validate_passport,
)
from inventory_app.validators.password_validators import ComplexPasswordValidator
from inventory_app.validators.business_validators import (
    PhoneValidator,
    PriceValidator,
    QuantityValidator,
)


# =============================================================================
# Tests de Cédula Ecuatoriana
# =============================================================================
class TestCedulaValidator(TestCase):
    """Tests para validación de cédula ecuatoriana (algoritmo módulo 10)."""

    def test_cedula_valida(self):
        """Cédulas reales válidas no deben lanzar error."""
        cedulas_validas = ['1710034065']
        for cedula in cedulas_validas:
            try:
                validate_ecuadorian_cedula(cedula)
            except ValidationError:
                self.fail(f"La cédula {cedula} debería ser válida.")

    def test_cedula_vacia(self):
        """Cédula vacía debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('')

    def test_cedula_none(self):
        """Cédula None debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula(None)

    def test_cedula_con_letras(self):
        """Cédula con letras debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('17100340AB')

    def test_cedula_muy_corta(self):
        """Cédula con menos de 10 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('171003')

    def test_cedula_muy_larga(self):
        """Cédula con más de 10 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('17100340651')

    def test_cedula_provincia_invalida(self):
        """Cédula con provincia > 24 debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('2510034065')

    def test_cedula_provincia_cero(self):
        """Cédula con provincia 00 debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('0010034065')

    def test_cedula_tercer_digito_invalido(self):
        """Cédula con tercer dígito > 5 debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('0170034065')

    def test_cedula_digito_verificador_incorrecto(self):
        """Cédula con dígito verificador incorrecto debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_cedula('1710034060')


# =============================================================================
# Tests de RUC Ecuatoriano
# =============================================================================
class TestRucValidator(TestCase):
    """Tests para validación de RUC ecuatoriano."""

    def test_ruc_persona_natural_valido(self):
        """RUC de persona natural (cédula + 001) debe ser válido."""
        try:
            validate_ecuadorian_ruc('1710034065001')
        except ValidationError:
            self.fail("RUC de persona natural válido no debería fallar.")

    def test_ruc_vacio(self):
        """RUC vacío debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('')

    def test_ruc_con_letras(self):
        """RUC con letras debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('171003406500A')

    def test_ruc_muy_corto(self):
        """RUC con menos de 13 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('1710034065')

    def test_ruc_muy_largo(self):
        """RUC con más de 13 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('17100340650011')

    def test_ruc_persona_natural_sin_001(self):
        """RUC de persona natural que no termina en 001 debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('1710034065002')

    def test_ruc_provincia_invalida(self):
        """RUC con provincia inválida debe fallar."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('2510034065001')

    def test_ruc_tercer_digito_invalido(self):
        """RUC con tercer dígito 7 u 8 debe fallar (no es natural, ni privada, ni pública)."""
        with self.assertRaises(ValidationError):
            validate_ecuadorian_ruc('0170000000001')


# =============================================================================
# Tests de Pasaporte
# =============================================================================
class TestPassportValidator(TestCase):
    """Tests para validación de pasaporte."""

    def test_pasaporte_valido_6_caracteres(self):
        """Pasaporte de 6 caracteres alfanuméricos debe ser válido."""
        validate_passport('AB1234')

    def test_pasaporte_valido_9_caracteres(self):
        """Pasaporte de 9 caracteres alfanuméricos debe ser válido."""
        validate_passport('ABC123456')

    def test_pasaporte_vacio(self):
        """Pasaporte vacío debe fallar."""
        with self.assertRaises(ValidationError):
            validate_passport('')

    def test_pasaporte_muy_corto(self):
        """Pasaporte de menos de 6 caracteres debe fallar."""
        with self.assertRaises(ValidationError):
            validate_passport('AB12')

    def test_pasaporte_muy_largo(self):
        """Pasaporte de más de 9 caracteres debe fallar."""
        with self.assertRaises(ValidationError):
            validate_passport('ABCDE12345')

    def test_pasaporte_con_espacios(self):
        """Pasaporte con espacios debe fallar."""
        with self.assertRaises(ValidationError):
            validate_passport('AB 1234')

    def test_pasaporte_con_caracteres_especiales(self):
        """Pasaporte con caracteres especiales debe fallar."""
        with self.assertRaises(ValidationError):
            validate_passport('AB-1234')


# =============================================================================
# Tests de Contraseña
# =============================================================================
class TestPasswordValidator(TestCase):
    """Tests para validación de contraseña compleja."""

    def setUp(self):
        self.validator = ComplexPasswordValidator()

    def test_password_valida(self):
        """Contraseña que cumple todos los requisitos no debe fallar."""
        self.validator.validate('MiPassword1!')

    def test_password_muy_corta(self):
        """Contraseña de menos de 8 caracteres debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('Ab1!')

    def test_password_sin_mayuscula(self):
        """Contraseña sin mayúscula debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('mipassword1!')

    def test_password_sin_minuscula(self):
        """Contraseña sin minúscula debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('MIPASSWORD1!')

    def test_password_sin_numero(self):
        """Contraseña sin número debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('MiPassword!')

    def test_password_sin_caracter_especial(self):
        """Contraseña sin carácter especial debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('MiPassword1')

    def test_password_solo_numeros(self):
        """Contraseña de solo números debe fallar."""
        with self.assertRaises(ValidationError):
            self.validator.validate('12345678')


# =============================================================================
# Tests de Teléfono
# =============================================================================
class TestPhoneValidator(TestCase):
    """Tests para validación de teléfono Ecuador (10 dígitos)."""

    def test_telefono_valido(self):
        """Teléfono de 10 dígitos debe ser válido."""
        PhoneValidator.validate('0991234567')

    def test_telefono_con_letras(self):
        """Teléfono con letras debe fallar."""
        with self.assertRaises(ValidationError):
            PhoneValidator.validate('099123ABCD')

    def test_telefono_muy_corto(self):
        """Teléfono de menos de 10 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            PhoneValidator.validate('09912345')

    def test_telefono_muy_largo(self):
        """Teléfono de más de 10 dígitos debe fallar."""
        with self.assertRaises(ValidationError):
            PhoneValidator.validate('09912345678')


# =============================================================================
# Tests de Precio
# =============================================================================
class TestPriceValidator(TestCase):
    """Tests para validación de precios."""

    def test_precio_positivo(self):
        """Precio positivo debe ser válido."""
        PriceValidator.validate(Decimal('10.50'))

    def test_precio_cero(self):
        """Precio cero debe ser válido."""
        PriceValidator.validate(Decimal('0'))

    def test_precio_negativo(self):
        """Precio negativo debe fallar."""
        with self.assertRaises(ValidationError):
            PriceValidator.validate(Decimal('-1.00'))


# =============================================================================
# Tests de Cantidad
# =============================================================================
class TestQuantityValidator(TestCase):
    """Tests para validación de cantidades."""

    def test_cantidad_positiva(self):
        """Cantidad positiva debe ser válida."""
        QuantityValidator.validate_positive(5)

    def test_cantidad_cero(self):
        """Cantidad cero debe fallar."""
        with self.assertRaises(ValidationError):
            QuantityValidator.validate_positive(0)

    def test_cantidad_negativa(self):
        """Cantidad negativa debe fallar."""
        with self.assertRaises(ValidationError):
            QuantityValidator.validate_positive(-1)

    def test_cantidad_none(self):
        """Cantidad None debe fallar."""
        with self.assertRaises(ValidationError):
            QuantityValidator.validate_positive(None)

    def test_cantidad_minimo_uno_valida(self):
        """Cantidad 1 debe ser válida con validate_min_one."""
        QuantityValidator.validate_min_one(1)

    def test_cantidad_minimo_uno_cero(self):
        """Cantidad 0 debe fallar con validate_min_one."""
        with self.assertRaises(ValidationError):
            QuantityValidator.validate_min_one(0)
