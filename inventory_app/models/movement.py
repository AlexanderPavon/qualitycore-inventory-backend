# models/movement.py
from django.db import models
from django.core.validators import MinValueValidator
from .product import Product
from .user import User
from .customer import Customer
from inventory_app.managers import SoftDeleteManager
from inventory_app.constants import MovementType, ValidationMessages

class Movement(models.Model):
    # Usar constantes centralizadas
    MOVEMENT_CHOICES = MovementType.CHOICES

    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)  # Optimizado con choices
    date = models.DateTimeField(db_index=True)  # Índice para filtrado y ordenamiento por fecha
    quantity = models.IntegerField(
        validators=[MinValueValidator(1, message=ValidationMessages.QUANTITY_MIN_ONE)]
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movements')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Precio histórico al momento del movimiento
    stock_in_movement = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    sale = models.ForeignKey('Sale', null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    purchase = models.ForeignKey('Purchase', null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros

    def __str__(self):
        return f"{self.movement_type} - {self.quantity} of {self.product.name}"
