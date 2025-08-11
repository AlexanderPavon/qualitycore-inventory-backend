# views/quotation_view.py
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.quotation import Quotation
from inventory_app.models.report import Report
from inventory_app.serializers.quotation_serializer import QuotationSerializer
from datetime import datetime
import os
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.conf import settings
from django.http import FileResponse, Http404  # 👈 nuevos imports

class QuotationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        products = data.pop('quoted_products')

        try:
            subtotal = sum(Decimal(p['unit_price']) * int(p['quantity']) for p in products)
        except (KeyError, ValueError, TypeError) as e:
            return Response({"error": f"Datos inválidos en productos: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        vat = round(subtotal * Decimal('0.15'), 2)
        total = subtotal + vat

        data['subtotal'] = subtotal
        data['tax'] = vat
        data['total'] = total
        data['user'] = request.user.id

        serializer = QuotationSerializer(data={**data, 'quoted_products': products})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Cotización guardada correctamente', 'quotation': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class QuotationListView(generics.ListAPIView):
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.rol == "Administrator":
            return Quotation.objects.filter(deleted_at__isnull=True).order_by('-date')
        else:
            return Quotation.objects.filter(user=user, deleted_at__isnull=True).order_by('-date')

class QuotationDetailView(generics.RetrieveAPIView):
    queryset = Quotation.objects.filter(deleted_at__isnull=True)
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated]

class QuotationPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(id=quotation_id, deleted_at__isnull=True)
        except Quotation.DoesNotExist:
            raise Http404("Cotización no encontrada")

        # ruta destino del PDF
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"cotizacion_{quotation.id}_{now}.pdf"
        out_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        # --- generar PDF (tu mismo código, SOLO cambia que el destino es `filepath`) ---
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='HeaderTitle', fontSize=22, alignment=1, spaceAfter=14))
        styles.add(ParagraphStyle(name='Totales', fontSize=11, textColor=colors.HexColor("#256029")))
        styles.add(ParagraphStyle(name='TotalBold', fontSize=12, textColor=colors.HexColor("#1f2937"), spaceBefore=5))
        styles.add(ParagraphStyle(name='ObsStyle', fontSize=10, textColor=colors.HexColor("#14532d")))

        elements = []

        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=90, height=40)
            img.hAlign = 'RIGHT'
            elements.append(img)

        elements.append(Paragraph("COTIZACIÓN", styles['HeaderTitle']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Fecha:</b> {quotation.date.strftime('%d/%m/%Y')}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Cliente:</b> {quotation.customer.name}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Vendedor:</b> {quotation.user.name}", styles["Normal"]))
        elements.append(Spacer(1, 18))

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

        elements.append(Paragraph(f"<b>Subtotal:</b> ${quotation.subtotal:.2f}", styles["Totales"]))
        elements.append(Paragraph(f"<b>IVA (15%):</b> ${quotation.tax:.2f}", styles["Totales"]))
        elements.append(Paragraph(f"<b>Total:</b> <b>${quotation.total:.2f}</b>", styles["TotalBold"]))

        # OJO: si tu modelo usa 'observations' en lugar de 'notes', cámbialo aquí
        if getattr(quotation, "notes", None):
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("<b>OBSERVACIONES:</b>", styles["Normal"]))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(quotation.notes, styles["ObsStyle"]))

        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<i>⚠ Cotización válida por 30 días</i>", styles["Normal"]))

        doc.build(elements)
        # --- fin generación PDF ---

        # opcional: registra el reporte en BD
        Report.objects.create(file=f"reports/{filename}", user=request.user)

        # 👉 DEVUELVE EL PDF, no JSON
        return FileResponse(open(filepath, "rb"),
                           content_type="application/pdf",
                           as_attachment=False,     # True si quieres forzar descarga
                           filename=filename)