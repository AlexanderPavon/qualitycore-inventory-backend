# models/product.py
from django.db import models
from django.core.validators import MinValueValidator
from .category import Category
from .supplier import Supplier
from inventory_app.managers import SoftDeleteManager
from inventory_app.validators import validate_image_size, validate_image_dimensions
from inventory_app.constants import ValidationMessages

class Product(models.Model):
    name = models.CharField(max_length=100, db_index=True)  # Índice para búsquedas rápidas por nombre
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, message=ValidationMessages.PRICE_NEGATIVE)]
    )
    current_stock = models.PositiveIntegerField(default=0)  # Solo valores >= 0 (no puede ser negativo)
    minimum_stock = models.PositiveIntegerField()  # Solo valores >= 0
    status = models.CharField(max_length=50)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='products')
    image = models.ImageField(
        upload_to="products/",
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_dimensions]  # Validación de tamaño y dimensiones
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros (incluidos eliminados)

    def __str__(self):
        return self.name
