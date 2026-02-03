"""
Validadores para documentos de identificación ecuatorianos.
"""
from django.core.exceptions import ValidationError


def validate_ecuadorian_cedula(cedula):
    """
    Valida cédula ecuatoriana de 10 dígitos usando el algoritmo del módulo 10.

    Args:
        cedula: String de 10 dígitos

    Raises:
        ValidationError: Si la cédula no es válida
    """
    if not cedula:
        raise ValidationError("La cédula no puede estar vacía.")

    # Verificar que sean exactamente 10 dígitos
    if not cedula.isdigit() or len(cedula) != 10:
        raise ValidationError("La cédula debe contener exactamente 10 dígitos numéricos.")

    # Los dos primeros dígitos deben corresponder a una provincia válida (01-24)
    provincia = int(cedula[0:2])
    if provincia < 1 or provincia > 24:
        raise ValidationError("Los dos primeros dígitos de la cédula deben corresponder a una provincia válida (01-24).")

    # El tercer dígito debe ser menor a 6 (0-5) para cédulas de personas naturales
    if int(cedula[2]) > 5:
        raise ValidationError("El tercer dígito de la cédula debe ser menor a 6.")

    # Validación del dígito verificador usando algoritmo módulo 10
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0

    for i in range(9):
        valor = int(cedula[i]) * coeficientes[i]
        if valor >= 10:
            valor -= 9
        suma += valor

    residuo = suma % 10
    digito_verificador = 0 if residuo == 0 else 10 - residuo

    if digito_verificador != int(cedula[9]):
        raise ValidationError("La cédula ingresada no es válida según el dígito verificador.")


def validate_ecuadorian_ruc(ruc):
    """
    Valida RUC ecuatoriano de 13 dígitos.

    Tipos de RUC:
    - Persona Natural: 10 dígitos de cédula + 001
    - Sociedad Privada: tercer dígito = 9
    - Sociedad Pública: tercer dígito = 6

    Args:
        ruc: String de 13 dígitos

    Raises:
        ValidationError: Si el RUC no es válido
    """
    if not ruc:
        raise ValidationError("El RUC no puede estar vacío.")

    # Verificar que sean exactamente 13 dígitos
    if not ruc.isdigit() or len(ruc) != 13:
        raise ValidationError("El RUC debe contener exactamente 13 dígitos numéricos.")

    # Los dos primeros dígitos deben corresponder a una provincia válida (01-24)
    provincia = int(ruc[0:2])
    if provincia < 1 or provincia > 24:
        raise ValidationError("Los dos primeros dígitos del RUC deben corresponder a una provincia válida (01-24).")

    tercer_digito = int(ruc[2])

    # RUC de Persona Natural (tercer dígito < 6)
    if tercer_digito < 6:
        # Los primeros 10 dígitos deben ser una cédula válida
        try:
            validate_ecuadorian_cedula(ruc[0:10])
        except ValidationError as e:
            raise ValidationError(f"El RUC de persona natural contiene una cédula inválida: {str(e)}")

        # Los últimos 3 dígitos deben ser 001
        if ruc[10:13] != "001":
            raise ValidationError("El RUC de persona natural debe terminar en 001.")

    # RUC de Sociedad Privada (tercer dígito = 9)
    elif tercer_digito == 9:
        # Validar con algoritmo módulo 11 para sociedades privadas
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coeficientes[i] for i in range(9))

        residuo = suma % 11
        digito_verificador = 0 if residuo == 0 else 11 - residuo

        if digito_verificador != int(ruc[9]):
            raise ValidationError("El RUC de sociedad privada no es válido según el dígito verificador.")

        # Los últimos 3 dígitos deben ser 001
        if ruc[10:13] != "001":
            raise ValidationError("El RUC de sociedad privada debe terminar en 001.")

    # RUC de Sociedad Pública (tercer dígito = 6)
    elif tercer_digito == 6:
        # Validar con algoritmo módulo 11 para sociedades públicas
        coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coeficientes[i] for i in range(8))

        residuo = suma % 11
        digito_verificador = 0 if residuo == 0 else 11 - residuo

        if digito_verificador != int(ruc[8]):
            raise ValidationError("El RUC de sociedad pública no es válido según el dígito verificador.")

        # Los últimos 4 dígitos deben ser 0001
        if ruc[9:13] != "0001":
            raise ValidationError("El RUC de sociedad pública debe terminar en 0001.")

    else:
        raise ValidationError(f"El tercer dígito del RUC ({tercer_digito}) no corresponde a un tipo válido de RUC.")


def validate_passport(passport):
    """
    Valida formato de pasaporte: alfanumérico de 6-9 caracteres.

    Args:
        passport: String alfanumérico

    Raises:
        ValidationError: Si el pasaporte no es válido
    """
    if not passport:
        raise ValidationError("El pasaporte no puede estar vacío.")

    # Verificar longitud
    if len(passport) < 6 or len(passport) > 9:
        raise ValidationError("El pasaporte debe contener entre 6 y 9 caracteres.")

    # Verificar que sea alfanumérico (letras y números, sin espacios ni caracteres especiales)
    if not passport.isalnum():
        raise ValidationError("El pasaporte debe ser alfanumérico (solo letras y números).")
