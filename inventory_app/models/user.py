# models/user.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from inventory_app.managers.soft_delete_manager import SoftDeleteQuerySet
from inventory_app.constants import UserRole, ValidationMessages

class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo User con soporte para soft delete.
    """
    use_in_migrations = True

    def get_queryset(self):
        """Filtra automáticamente usuarios eliminados (soft delete)"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email debe ser obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

    def all_with_deleted(self):
        """Retorna todos los usuarios, incluidos los eliminados"""
        return SoftDeleteQuerySet(self.model, using=self._db)

class User(AbstractUser):
    username = None
    email = models.EmailField(
        'email address',
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'Ya existe un usuario con este correo electrónico.'
        }
    )  # Índice explícito para búsquedas
    name = models.CharField(max_length=100)

    # Usar constantes centralizadas
    ROLE_CHOICES = UserRole.CHOICES
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)

    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=False,
        null=False,
        error_messages={
            'unique': 'Ya existe un usuario con este teléfono.'
        },
        validators=[
            RegexValidator(
                regex=ValidationMessages.PHONE_REGEX,
                message=ValidationMessages.PHONE_INVALID_FORMAT,
                code='invalid_phone'
            )
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'role']

    objects = UserManager()  # Filtra automáticamente usuarios eliminados
    all_objects = models.Manager()  # Acceso a todos los usuarios (incluidos eliminados)

    def __str__(self):
        return self.email
