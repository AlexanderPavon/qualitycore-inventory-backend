# models/supplier.py
from django.db import models
from django.db.models import Q
from django.core.validators import RegexValidator, EmailValidator
from inventory_app.managers import SoftDeleteManager
from inventory_app.constants import ValidationMessages
from inventory_app.validators.ecuadorian_validators import (
    validate_ecuadorian_cedula,
    validate_ecuadorian_ruc,
    validate_passport,
)

class Supplier(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('cedula', 'Cédula'),
        ('ruc', 'RUC'),
        ('passport', 'Pasaporte'),
    ]

    name = models.CharField(max_length=100, db_index=True)

    email = models.EmailField(
        max_length=100,
        validators=[
            EmailValidator(message="El correo electrónico no es válido.")
        ]
    )

    document_type = models.CharField(
        max_length=10,
        choices=DOCUMENT_TYPE_CHOICES,
        default='ruc'
    )

    tax_id = models.CharField(max_length=13)

    phone = models.CharField(
        max_length=10,
        blank=False,
        null=False,
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_supplier_email'
            ),
            models.UniqueConstraint(
                fields=['tax_id'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_supplier_tax_id'
            ),
            models.UniqueConstraint(
                fields=['phone'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_supplier_phone'
            ),
        ]

    def clean(self):
        if self.document_type and self.tax_id:
            if self.document_type == 'cedula':
                validate_ecuadorian_cedula(self.tax_id)
            elif self.document_type == 'ruc':
                validate_ecuadorian_ruc(self.tax_id)
            elif self.document_type == 'passport':
                validate_passport(self.tax_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
