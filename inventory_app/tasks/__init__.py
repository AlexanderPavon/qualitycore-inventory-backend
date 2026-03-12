# tasks/__init__.py
"""
Tareas asíncronas de Celery.

Re-exporta todas las tareas desde sus módulos especializados para que
las importaciones existentes (from inventory_app.tasks import X) sigan funcionando.

Módulos:
  pdf_tasks     — Generación de PDFs (cotizaciones y reportes)
  audit_tasks   — Escritura asíncrona de AuditLog
  cleanup_tasks — Limpieza periódica de reportes antiguos
"""
from .pdf_tasks import (
    generate_quotation_pdf,
    generate_movements_report_pdf,
    generate_report_pdf,
)
from .audit_tasks import log_audit_action
from .cleanup_tasks import cleanup_old_reports

__all__ = [
    'generate_quotation_pdf',
    'generate_movements_report_pdf',
    'generate_report_pdf',
    'log_audit_action',
    'cleanup_old_reports',
]
