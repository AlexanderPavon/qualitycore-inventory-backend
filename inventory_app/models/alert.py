# models/alert.py
from django.db import models
from .product import Product
from inventory_app.managers import SoftDeleteManager
from inventory_app.constants import AlertType

class Alert(models.Model):
    type = models.CharField(max_length=20, choices=AlertType.CHOICES, default=AlertType.LOW_STOCK)
    message = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros

    def __str__(self):
        return f"[{self.get_type_display()}] {self.product.name}"
