# models/category.py
from django.db import models
from django.db.models import Q
from inventory_app.managers import SoftDeleteManager

class Category(models.Model):
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_category_name'
            ),
        ]

    def __str__(self):
        return self.name
