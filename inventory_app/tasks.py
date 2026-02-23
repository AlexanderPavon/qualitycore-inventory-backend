# tasks.py
"""
Tareas asíncronas de Celery para operaciones pesadas.
Principalmente generación de PDFs de cotizaciones y reportes.
"""
import os
from decimal import Decimal
from datetime import datetime, timedelta
from celery import shared_task
from inventory_app.utils.timezone_utils import to_local, local_now
from django.conf import settings
from django.db.models import Sum
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from inventory_app.models.quotation import Quotation
from inventory_app.models.movement import Movement
from inventory_app.models.report import Report
from inventory_app.constants import BusinessRules
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
        local_date = to_local(quotation.date)
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
        iva_pct = int(BusinessRules.TAX_RATE * 100)
        elements.append(Paragraph(f"<b>IVA ({iva_pct}%):</b> ${quotation.tax:.2f}", styles["Totales"]))
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
        current_datetime = local_now().strftime("%Y-%m-%d_%H-%M-%S")
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
        elements.append(Paragraph(f"<b>Generado:</b> {local_now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 18))

        # Tabla de movimientos
        data = [["Fecha", "Tipo", "Producto", "Cantidad", "Stock"]]
        for mov in movements:
            tipo = "Entrada" if mov.movement_type == "input" else "Salida"
            data.append([
                to_local(mov.date).strftime('%d/%m/%Y'),
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


@shared_task(bind=True, max_retries=3)
def generate_report_pdf(self, user_id, report_type, start_date=None, end_date=None):
    """
    Genera un PDF de reporte de forma asíncrona.

    Args:
        user_id: ID del usuario que solicita el reporte
        report_type: "movimientos" o "top_vendidos"
        start_date: Fecha inicio (formato "YYYY-MM-DD", opcional)
        end_date: Fecha fin (formato "YYYY-MM-DD", opcional)

    Returns:
        str: Ruta relativa del archivo PDF generado
    """
    try:
        from inventory_app.models.user import User

        user = User.objects.get(id=user_id)

        # Parsear fechas
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = (
            datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            if end_date else None
        )

        now = local_now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"report_{report_type}_{now}.pdf"
        out_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CustomTitle', fontSize=20, alignment=1, spaceAfter=12))
        styles.add(ParagraphStyle(name='CustomInfo', fontSize=10, textColor=colors.gray, spaceAfter=6))
        styles.add(ParagraphStyle(name='CustomNote', fontSize=9, textColor=colors.HexColor("#256029"), spaceBefore=10))

        elements = []

        # Logo
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=90, height=40)
            img.hAlign = 'RIGHT'
            elements.append(img)

        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        elements.append(Spacer(1, 6))

        title = "PRODUCTOS MÁS VENDIDOS" if report_type == "top_vendidos" else "REPORTE DE MOVIMIENTOS DE INVENTARIO"
        elements.append(Paragraph(title, styles["CustomTitle"]))
        elements.append(Spacer(1, 6))

        elements.append(Paragraph(f"Generado por: {user.name}", styles["CustomInfo"]))
        elements.append(Paragraph(f"Fecha: {local_now().strftime('%d/%m/%Y %H:%M:%S')}", styles["CustomInfo"]))
        if start_date or end_date:
            start_label = start_dt.strftime("%d/%m/%Y") if start_dt else "—"
            end_label = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y") if end_date else "—"
            elements.append(Paragraph(f"Período: {start_label}  a  {end_label}", styles["CustomInfo"]))
        elements.append(Spacer(1, 14))

        if report_type == "top_vendidos":
            sales = (
                Movement.objects.filter(movement_type="output", deleted_at__isnull=True)
                .filter(date__gte=start_dt if start_dt else "2000-01-01")
                .filter(date__lte=end_dt if end_dt else datetime.now())
                .values("product__name")
                .annotate(total_sold=Sum("quantity"))
                .order_by("-total_sold")[:10]
            )

            data = [["Producto", "Cantidad Vendida"]]
            for s in sales:
                data.append([s["product__name"], s["total_sold"]])

            table = Table(data, colWidths=[250, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Este reporte contiene los 10 productos más vendidos.", styles["CustomNote"]))

        else:
            movements = Movement.objects.filter(deleted_at__isnull=True)
            if start_dt:
                movements = movements.filter(date__gte=start_dt)
            if end_dt:
                movements = movements.filter(date__lte=end_dt)

            movements = movements.select_related(
                'product', 'product__supplier', 'customer', 'user'
            ).order_by("-date")[:50]

            data = [["Fecha", "Tipo", "Producto", "Cantidad", "Cliente / Proveedor", "Usuario"]]
            for m in movements:
                date = to_local(m.date).strftime("%d/%m/%Y %H:%M")
                type_mov = "Entrada" if m.movement_type == "input" else "Salida"
                product = m.product.name
                qty = str(m.quantity)
                related = ""
                if m.movement_type == "output" and m.customer:
                    related = m.customer.name
                elif m.movement_type == "input" and m.product.supplier:
                    related = m.product.supplier.name
                user_name = m.user.name if m.user else "N/A"
                data.append([date, type_mov, product, qty, related, user_name])

            table = Table(data, colWidths=[90, 60, 120, 50, 120, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Este reporte contiene hasta 50 de los movimientos más recientes.", styles["CustomNote"]))

        doc.build(elements)

        # Registrar en BD
        Report.objects.create(file=f"reports/{filename}", user=user)

        logger.info(f"PDF de reporte '{report_type}' generado exitosamente: {filename}")
        return f"reports/{filename}"

    except Exception as exc:
        logger.error(f"Error generando reporte '{report_type}': {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
