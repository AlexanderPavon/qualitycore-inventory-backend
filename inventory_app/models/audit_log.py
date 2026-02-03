# models/audit_log.py
"""
Modelo para almacenar un audit trail de cambios críticos en la base de datos.
Registra quién modificó qué y cuándo.
"""
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Registro de auditoría para cambios importantes en el sistema.
    """
    ACTION_CHOICES = [
        ('create', 'Crear'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('permission_denied', 'Permiso denegado'),
    ]

    # Quién realizó la acción
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    user_email = models.EmailField(max_length=255, blank=True)  # Backup si el usuario es eliminado

    # Qué se hizo
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)  # Nombre del modelo afectado
    object_id = models.IntegerField(null=True, blank=True)  # ID del objeto afectado
    object_repr = models.CharField(max_length=200, blank=True)  # Representación del objeto

    # Detalles del cambio
    changes = models.JSONField(null=True, blank=True)  # Campos modificados (antes/después)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Cuándo
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'user']),
            models.Index(fields=['model_name', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.user_email} - {self.action} {self.model_name} at {self.timestamp}"

    @staticmethod
    def log_action(user, action, model_name, obj=None, changes=None, request=None):
        """
        Método helper para crear logs de auditoría fácilmente.

        Args:
            user: Usuario que realiza la acción
            action: Tipo de acción ('create', 'update', 'delete', etc.)
            model_name: Nombre del modelo afectado
            obj: Instancia del objeto afectado (opcional)
            changes: Diccionario con los cambios realizados (opcional)
            request: Objeto request de Django (para obtener IP y user agent)
        """
        log = AuditLog(
            user=user if user and user.is_authenticated else None,
            user_email=user.email if user and user.is_authenticated else 'anonymous',
            action=action,
            model_name=model_name,
            changes=changes
        )

        if obj:
            log.object_id = obj.pk
            log.object_repr = str(obj)[:200]

        if request:
            # Obtener IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                log.ip_address = x_forwarded_for.split(',')[0]
            else:
                log.ip_address = request.META.get('REMOTE_ADDR')

            # Obtener User Agent
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        log.save()
        return log
