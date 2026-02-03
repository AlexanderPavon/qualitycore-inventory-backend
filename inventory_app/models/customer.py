# models/customer.py
from django.db import models
from django.core.validators import RegexValidator
from inventory_app.managers import SoftDeleteManager
from inventory_app.constants import ValidationMessages

class Customer(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('cedula', 'Cédula'),
        ('ruc', 'RUC'),
        ('passport', 'Pasaporte'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(
        max_length=100,
        unique=True,
        error_messages={
            'unique': 'Ya existe un cliente con este correo electrónico.'
        }
    )
    document_type = models.CharField(
        max_length=10,
        choices=DOCUMENT_TYPE_CHOICES,
        default='cedula'
    )
    document = models.CharField(
        max_length=13,
        unique=True,
        error_messages={
            'unique': 'Ya existe un cliente con este documento.'
        }
    )
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=False,
        null=False,
        error_messages={
            'unique': 'Ya existe un cliente con este teléfono.'
        },
        validators=[
            RegexValidator(
                regex=ValidationMessages.PHONE_REGEX,
                message=ValidationMessages.PHONE_INVALID_FORMAT
            )
        ]
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros

    def __str__(self):
        return self.name
