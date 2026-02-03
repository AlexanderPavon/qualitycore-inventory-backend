# models/purchase.py
from django.db import models
from django.core.validators import MinValueValidator
from .supplier import Supplier
from .user import User
from inventory_app.managers import SoftDeleteManager

class Purchase(models.Model):
    """
    Modelo para agrupar múltiples movimientos de entrada (compras) en una sola orden.
    Similar a Sale pero para entradas de inventario.
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='purchases')
    date = models.DateTimeField(db_index=True)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Compra #{self.id} - {self.supplier.name}"

    class Meta:
        ordering = ['-date']
