# views/report_view.py
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.report import Report
from inventory_app.models.movement import Movement
from inventory_app.serializers.report_serializer import ReportSerializer
from datetime import datetime, timedelta
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.db.models import Sum
from django.urls import reverse
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from pathlib import Path
import os

class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        # opcional: limitar al dueño o admin
        # if report.user != request.user and getattr(request.user, "role", "") != "Administrator":
        #     return Response(status=status.HTTP_403_FORBIDDEN)

        file_path = Path(settings.MEDIA_ROOT) / report.file.name  # e.g. reports/xxxx.pdf
        if not file_path.exists():
            raise Http404("Archivo no encontrado")

        resp = FileResponse(open(file_path, "rb"), content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{file_path.name}"'
        return resp

class ReportListView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user).order_by("-generated_at")


class ReportGeneratePDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        report_type = request.data.get("type", "movimientos")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_dt = (
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                if end_date else None
            )
        except Exception:
            return Response({"message": "Fechas inválidas"}, status=status.HTTP_400_BAD_REQUEST)

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"reporte_{report_type}_{now}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(name='CustomTitle', fontSize=20, alignment=1, spaceAfter=12))
        styles.add(ParagraphStyle(name='CustomInfo', fontSize=10, textColor=colors.gray, spaceAfter=6))
        styles.add(ParagraphStyle(name='CustomNote', fontSize=9, textColor=colors.HexColor("#256029"), spaceBefore=10))

        elements = []

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
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles["CustomInfo"]))
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
            movements = movements.order_by("-date")[:50]

            data = [["Fecha", "Tipo", "Producto", "Cantidad", "Cliente / Proveedor", "Usuario"]]
            for m in movements:
                date = m.date.strftime("%d/%m/%Y %H:%M")
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

        report = Report.objects.create(
            file=f"reports/{filename}",
            user=request.user
        )

        return Response({
            "message": "Reporte generado correctamente",
            "url": reverse("report-download", args=[report.id]) 
        })