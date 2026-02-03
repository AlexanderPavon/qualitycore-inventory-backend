# tasks.py
"""
Tareas asíncronas de Celery para operaciones pesadas.
Principalmente generación de PDFs de cotizaciones y reportes.
"""
import os
from decimal import Decimal
from datetime import datetime
from celery import shared_task
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from inventory_app.models.quotation import Quotation
from inventory_app.models.movement import Movement
from inventory_app.models.report import Report
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_quotation_pdf(self, quotation_id, user_id):
    """
    Genera un PDF de cotización de forma asíncrona.

    Args:
        quotation_id: ID de la cotización
        user_id: ID del usuario que solicita el PDF

    Returns:
        str: Ruta relativa del archivo PDF generado
    """
    try:
        quotation = Quotation.objects.select_related(
            'customer',
            'user'
        ).prefetch_related(
            'quoted_products__product'
        ).get(id=quotation_id, deleted_at__isnull=True)

        # Generar nombre personalizado con fecha, hora e ID
        # Convertir de UTC a zona horaria local (Ecuador)
        from zoneinfo import ZoneInfo
        ecuador_tz = ZoneInfo('America/Guayaquil')
        local_date = quotation.date.astimezone(ecuador_tz)
        datetime_str = local_date.strftime("%Y-%m-%d_%H-%M-%S")
        customer_name = quotation.customer.name.replace(" ", "_").replace("/", "-")
        filename = f"quotation_{quotation.id}_{customer_name}_{datetime_str}.pdf"

        out_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        # Generar PDF
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='HeaderTitle', fontSize=22, alignment=1, spaceAfter=14))
        styles.add(ParagraphStyle(name='Totales', fontSize=11, textColor=colors.HexColor("#256029")))
        styles.add(ParagraphStyle(name='TotalBold', fontSize=12, textColor=colors.HexColor("#1f2937"), spaceBefore=5))
        styles.add(ParagraphStyle(name='ObsStyle', fontSize=10, textColor=colors.HexColor("#14532d")))

        elements = []

        # Logo
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=90, height=40)
            img.hAlign = 'RIGHT'
            elements.append(img)

        # Encabezado
        elements.append(Paragraph("COTIZACIÓN", styles['HeaderTitle']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Fecha:</b> {local_date.strftime('%d/%m/%Y')}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Cliente:</b> {quotation.customer.name}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Vendedor:</b> {quotation.user.name}", styles["Normal"]))
        elements.append(Spacer(1, 18))

        # Tabla de productos
        data = [["Producto", "Cantidad", "Precio Unitario", "Subtotal"]]
        for p in quotation.quoted_products.all():
            data.append([
                p.product.name,
                p.quantity,
                f"${p.unit_price:.2f}",
                f"${p.subtotal:.2f}"
            ])

        table = Table(data, colWidths=[200, 80, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
        ]))
        elements.append(table)
        elements.append(Spacer(1, 18))

        # Totales
        elements.append(Paragraph(f"<b>Subtotal:</b> ${quotation.subtotal:.2f}", styles["Totales"]))
        elements.append(Paragraph(f"<b>IVA (15%):</b> ${quotation.tax:.2f}", styles["Totales"]))
        elements.append(Paragraph(f"<b>Total:</b> <b>${quotation.total:.2f}</b>", styles["TotalBold"]))

        # Observaciones
        if getattr(quotation, "notes", None):
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("<b>OBSERVACIONES:</b>", styles["Normal"]))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(quotation.notes, styles["ObsStyle"]))

        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<i>⚠ Cotización válida por 30 días</i>", styles["Normal"]))

        doc.build(elements)

        # Registrar en BD
        from inventory_app.models.user import User
        user = User.objects.get(id=user_id)
        Report.objects.create(file=f"reports/{filename}", user=user)

        logger.info(f"PDF de cotización generado exitosamente: {filename}")
        return f"reports/{filename}"

    except Quotation.DoesNotExist:
        logger.error(f"Cotización {quotation_id} no encontrada")
        raise
    except Exception as exc:
        logger.error(f"Error generando PDF de cotización {quotation_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_movements_report_pdf(self, user_id, filters=None):
    """
    Genera un PDF de reporte de movimientos de forma asíncrona.

    Args:
        user_id: ID del usuario que solicita el reporte
        filters: Diccionario con filtros opcionales (fecha_inicio, fecha_fin, tipo_movimiento)

    Returns:
        str: Ruta relativa del archivo PDF generado
    """
    try:
        from inventory_app.models.user import User

        # Construir queryset con filtros
        movements = Movement.objects.select_related(
            'product',
            'product__supplier',
            'customer',
            'user'
        ).filter(deleted_at__isnull=True)

        if filters:
            if filters.get('start_date'):
                movements = movements.filter(date__gte=filters['start_date'])
            if filters.get('end_date'):
                movements = movements.filter(date__lte=filters['end_date'])
            if filters.get('movement_type'):
                movements = movements.filter(movement_type=filters['movement_type'])

        movements = movements.order_by("-date")[:50]

        # Generar nombre del archivo con fecha, hora y segundos
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"movements_report_{current_datetime}.pdf"

        out_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        # Generar PDF
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='HeaderTitle', fontSize=20, alignment=1, spaceAfter=12))

        elements = []

        # Logo
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=90, height=40)
            img.hAlign = 'RIGHT'
            elements.append(img)

        # Encabezado
        elements.append(Paragraph("REPORTE DE MOVIMIENTOS", styles['HeaderTitle']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 18))

        # Tabla de movimientos
        data = [["Fecha", "Tipo", "Producto", "Cantidad", "Stock"]]
        for mov in movements:
            tipo = "Entrada" if mov.movement_type == "input" else "Salida"
            data.append([
                mov.date.strftime('%d/%m/%Y'),
                tipo,
                mov.product.name[:30],  # Truncar si es muy largo
                str(mov.quantity),
                str(mov.stock_in_movement)
            ])

        table = Table(data, colWidths=[80, 60, 200, 60, 60])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
        ]))
        elements.append(table)

        doc.build(elements)

        # Registrar en BD
        user = User.objects.get(id=user_id)
        Report.objects.create(file=f"reports/{filename}", user=user)

        logger.info(f"PDF de reporte de movimientos generado exitosamente: {filename}")
        return f"reports/{filename}"

    except Exception as exc:
        logger.error(f"Error generando reporte de movimientos: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
