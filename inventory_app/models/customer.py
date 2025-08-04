# models/customer.py
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator, EmailValidator

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(
        max_length=100,
    )
    document = models.CharField(
        max_length=13,
        validators=[
            RegexValidator(
                regex=r'^\d{10,13}$',
                message='La cédula o RUC debe tener entre 10 y 13 dígitos numéricos.'
            )
        ]
    )
    phone = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message='El teléfono solo debe contener números.'
            )
        ]
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
