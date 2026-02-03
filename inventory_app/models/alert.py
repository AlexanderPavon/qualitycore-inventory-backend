# models/alert.py
from django.db import models
from .product import Product
from inventory_app.managers import SoftDeleteManager

class Alert(models.Model):
    ALERT_TYPES = [
        ('low_stock', 'Stock bajo'),
        ('one_unit', 'Solo una unidad'),
        ('out_of_stock', 'Sin stock'),
    ]

    type = models.CharField(max_length=20, choices=ALERT_TYPES, default='low_stock')
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
