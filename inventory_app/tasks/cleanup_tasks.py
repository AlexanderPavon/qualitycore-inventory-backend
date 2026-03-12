# tasks/cleanup_tasks.py
"""
Tarea Celery para limpieza periódica de reportes PDF antiguos.
"""
from datetime import timedelta
from celery import shared_task
from inventory_app.models.report import Report
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_reports(days: int = 30):
    """
    Elimina reportes PDF más antiguos que `days` días.
    Borra tanto el archivo físico como el registro en BD.
    Se ejecuta automáticamente vía Celery Beat (ver CELERY_BEAT_SCHEDULE en settings).
    """
    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=days)
    old_reports = Report.objects.filter(generated_at__lt=cutoff)

    deleted_count = 0
    errors = 0

    for report in old_reports:
        try:
            # Borrar archivo físico (local o Cloudinary según configuración)
            if report.file:
                report.file.delete(save=False)
        except Exception as e:
            logger.warning(f"No se pudo eliminar el archivo del reporte {report.id}: {e}")
            errors += 1

    deleted_count, _ = old_reports.delete()

    logger.info(
        f"cleanup_old_reports: {deleted_count} reportes eliminados "
        f"(mayores a {days} días). Errores de archivo: {errors}."
    )
    return {"deleted": deleted_count, "file_errors": errors}
