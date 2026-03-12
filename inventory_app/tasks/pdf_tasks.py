# tasks/pdf_tasks.py
"""
Tareas Celery para generación asíncrona de PDFs.
"""
from datetime import datetime, timedelta
from celery import shared_task
from inventory_app.utils.timezone_utils import to_local, local_now
from inventory_app.utils.pdf_builder import PDFBuilder
from django.db.models import Sum
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
        from inventory_app.models.user import User

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

        builder = PDFBuilder(PDFBuilder.make_output_path(filename))
        builder.add_style('HeaderTitle', fontSize=22, alignment=1, spaceAfter=14)
        builder.add_style('Totales', fontSize=11, textColor='#256029')
        builder.add_style('TotalBold', fontSize=12, textColor='#1f2937', spaceBefore=5)
        builder.add_style('ObsStyle', fontSize=10, textColor='#14532d')

        builder.add_logo()
        builder.add_paragraph("COTIZACIÓN", 'HeaderTitle')
        builder.add_spacer(8)
        builder.add_paragraph(f"<b>Fecha:</b> {local_date.strftime('%d/%m/%Y')}")
        builder.add_paragraph(f"<b>Cliente:</b> {quotation.customer.name}")
        builder.add_paragraph(f"<b>Vendedor:</b> {quotation.user.name}")
        builder.add_spacer(18)

        # Tabla de productos
        data = [["Producto", "Cantidad", "Precio Unitario", "Subtotal"]]
        for p in quotation.quoted_products.all():
            data.append([
                p.product.name,
                p.quantity,
                f"${p.unit_price:.2f}",
                f"${p.subtotal:.2f}"
            ])
        builder.add_table(data, col_widths=[200, 80, 80, 80], header_color="#10b981", font_size=10)
        builder.add_spacer(18)

        # Totales
        builder.add_paragraph(f"<b>Subtotal:</b> ${quotation.subtotal:.2f}", 'Totales')
        iva_pct = int(BusinessRules.TAX_RATE * 100)
        builder.add_paragraph(f"<b>IVA ({iva_pct}%):</b> ${quotation.tax:.2f}", 'Totales')
        builder.add_paragraph(f"<b>Total:</b> <b>${quotation.total:.2f}</b>", 'TotalBold')

        # Observaciones
        if getattr(quotation, "notes", None):
            builder.add_spacer(12)
            builder.add_paragraph("<b>OBSERVACIONES:</b>")
            builder.add_spacer(4)
            builder.add_paragraph(quotation.notes, 'ObsStyle')

        builder.add_spacer(12)
        builder.add_paragraph("<i>⚠ Cotización válida por 30 días</i>")
        builder.build()

        # Registrar en BD
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

        total_count = movements.count()
        REPORT_LIMIT = 500
        movements = movements.order_by("-date")[:REPORT_LIMIT]

        # Generar nombre del archivo con fecha, hora y segundos
        current_datetime = local_now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"movements_report_{current_datetime}.pdf"

        builder = PDFBuilder(PDFBuilder.make_output_path(filename))
        builder.add_style('HeaderTitle', fontSize=20, alignment=1, spaceAfter=12)
        builder.add_style('TruncNote', fontSize=9, textColor='#b45309', spaceBefore=8)

        builder.add_logo()
        builder.add_paragraph("REPORTE DE MOVIMIENTOS", 'HeaderTitle')
        builder.add_spacer(8)
        builder.add_paragraph(f"<b>Generado:</b> {local_now().strftime('%d/%m/%Y %H:%M')}")
        if total_count > REPORT_LIMIT:
            builder.add_paragraph(
                f"⚠ Mostrando {REPORT_LIMIT} de {total_count} movimientos. "
                "Aplique filtros de fecha para ver períodos más acotados.",
                'TruncNote'
            )
        else:
            builder.add_paragraph(f"<b>Total de movimientos:</b> {total_count}")
        builder.add_spacer(18)

        # Tabla de movimientos
        data = [["Fecha", "Tipo", "Producto", "Cantidad", "Stock"]]
        for mov in movements:
            tipo = "Entrada" if mov.movement_type == "input" else "Salida"
            data.append([
                to_local(mov.date).strftime('%d/%m/%Y'),
                tipo,
                mov.product.name[:30],
                str(mov.quantity),
                str(mov.stock_in_movement)
            ])
        builder.add_table(data, col_widths=[80, 60, 200, 60, 60], header_color="#10b981", font_size=9)
        builder.build()

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

        # Estilos extra de cabecera para tablas de reportes
        report_header_extra = [
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
        ]

        builder = PDFBuilder(PDFBuilder.make_output_path(filename))
        builder.add_style('CustomTitle', fontSize=20, alignment=1, spaceAfter=12)
        builder.add_style('CustomInfo', fontSize=10, textColor='gray', spaceAfter=6)
        builder.add_style('CustomNote', fontSize=9, textColor='#256029', spaceBefore=10)

        builder.add_logo()
        builder.add_hr()
        builder.add_spacer(6)

        title = "PRODUCTOS MÁS VENDIDOS" if report_type == "top_vendidos" else "REPORTE DE MOVIMIENTOS DE INVENTARIO"
        builder.add_paragraph(title, 'CustomTitle')
        builder.add_spacer(6)

        builder.add_paragraph(f"Generado por: {user.name}", 'CustomInfo')
        builder.add_paragraph(f"Fecha: {local_now().strftime('%d/%m/%Y %H:%M:%S')}", 'CustomInfo')
        if start_date or end_date:
            start_label = start_dt.strftime("%d/%m/%Y") if start_dt else "—"
            end_label = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y") if end_date else "—"
            builder.add_paragraph(f"Período: {start_label}  a  {end_label}", 'CustomInfo')
        builder.add_spacer(14)

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

            builder.add_table(
                data,
                col_widths=[250, 100],
                header_color="#4f46e5",
                font_size=10,
                extra_styles=report_header_extra,
            )
            builder.add_spacer(16)
            builder.add_paragraph("Este reporte contiene los 10 productos más vendidos.", 'CustomNote')

        else:
            movements = Movement.objects.filter(deleted_at__isnull=True)
            if start_dt:
                movements = movements.filter(date__gte=start_dt)
            if end_dt:
                movements = movements.filter(date__lte=end_dt)

            total_movements = movements.count()
            REPORT_LIMIT = 500
            movements = movements.select_related(
                'product', 'product__supplier', 'customer', 'user'
            ).order_by("-date")[:REPORT_LIMIT]

            if total_movements > REPORT_LIMIT:
                builder.add_paragraph(
                    f"⚠ Mostrando {REPORT_LIMIT} de {total_movements} movimientos. "
                    "Aplique filtros de fecha para ver períodos más acotados.",
                    'CustomNote'
                )
                builder.add_spacer(8)
            else:
                builder.add_paragraph(f"Total de registros: {total_movements}", 'CustomInfo')
                builder.add_spacer(8)

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

            builder.add_table(
                data,
                col_widths=[90, 60, 120, 50, 120, 100],
                header_color="#4f46e5",
                font_size=9,
                extra_styles=report_header_extra,
            )
            builder.add_spacer(16)
            if total_movements <= REPORT_LIMIT:
                builder.add_paragraph(f"Reporte completo — {total_movements} movimientos.", 'CustomNote')

        builder.build()

        # Registrar en BD
        Report.objects.create(file=f"reports/{filename}", user=user)

        logger.info(f"PDF de reporte '{report_type}' generado exitosamente: {filename}")
        return f"reports/{filename}"

    except Exception as exc:
        logger.error(f"Error generando reporte '{report_type}': {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
