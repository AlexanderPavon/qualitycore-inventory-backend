# managers/soft_delete_manager.py
"""
Manager personalizado para manejar soft deletes de manera automática.
Filtra automáticamente los registros eliminados (deleted_at != null).
"""
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet personalizado que extiende el comportamiento de delete()
    para realizar soft deletes en lugar de eliminaciones físicas.
    """

    def delete(self):
        """
        Soft delete: marca los registros como eliminados sin borrarlos físicamente.
        """
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """
        Hard delete: elimina los registros físicamente de la base de datos.
        Usar con precaución.
        """
        return super().delete()

    def alive(self):
        """
        Filtra solo los registros activos (no eliminados).
        """
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """
        Filtra solo los registros eliminados.
        """
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    Manager que filtra automáticamente los registros soft-deleted.

    Uso:
        class MyModel(models.Model):
            deleted_at = models.DateTimeField(null=True, blank=True)

            objects = SoftDeleteManager()  # Excluye automáticamente deleted
            all_objects = models.Manager()  # Acceso a todos (incluidos deleted)

    Ejemplos:
        MyModel.objects.all()  # Solo registros activos
        MyModel.all_objects.all()  # Todos los registros
        MyModel.objects.dead()  # Solo registros eliminados
    """

    def get_queryset(self):
        """
        Retorna solo los registros donde deleted_at es NULL (no eliminados).
        """
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def dead(self):
        """
        Retorna solo los registros eliminados (soft deleted).
        """
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=False)

    def all_with_deleted(self):
        """
        Retorna todos los registros, incluidos los eliminados.
        """
        return SoftDeleteQuerySet(self.model, using=self._db)
