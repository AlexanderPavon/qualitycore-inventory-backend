# models/sale.py
from django.db import models
from django.core.validators import MinValueValidator
from .customer import Customer
from .user import User
from inventory_app.managers import SoftDeleteManager

class Sale(models.Model):
    """
    Representa una venta que agrupa múltiples movimientos de salida.
    Permite rastrear qué productos se vendieron juntos al mismo cliente.
    """
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales')
    date = models.DateTimeField(db_index=True)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total de la venta calculado automáticamente"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['customer', '-date']),
        ]

    def __str__(self):
        return f"Sale #{self.id} - {self.customer.name} - ${self.total}"
