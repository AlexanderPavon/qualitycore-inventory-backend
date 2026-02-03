# utils/exception_handler.py
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import ValidationError

def custom_exception_handler(exc, context):
    """
    Custom exception handler que remueve los prefijos de nombre de campo
    de los mensajes de error de validación de DRF.
    """
    # Llamar al exception handler por defecto primero
    response = drf_exception_handler(exc, context)

    if response is not None and isinstance(exc, ValidationError):
        # Si hay errores de validación, reformatearlos
        if isinstance(response.data, dict):
            formatted_errors = {}

            for field, errors in response.data.items():
                # Si el error es una lista de mensajes
                if isinstance(errors, list):
                    # Tomar solo los mensajes sin el prefijo del campo
                    formatted_errors[field] = errors
                else:
                    formatted_errors[field] = [str(errors)]

            response.data = formatted_errors

    return response
