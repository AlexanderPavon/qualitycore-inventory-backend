# views/quotation_view.py
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.quotation import Quotation
from inventory_app.models.report import Report
from inventory_app.serializers.quotation_serializer import QuotationSerializer
from inventory_app.tasks import generate_quotation_pdf
from inventory_app.constants import UserRole
from datetime import datetime
import os
from decimal import Decimal
from django.conf import settings
from django.http import FileResponse, Http404
import logging

logger = logging.getLogger(__name__)

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
        if user.role in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN]:
            return Quotation.objects.filter(deleted_at__isnull=True).order_by('-date')
        else:
            return Quotation.objects.filter(user=user, deleted_at__isnull=True).order_by('-date')

class QuotationDetailView(generics.RetrieveAPIView):
    queryset = Quotation.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated]

class QuotationPDFView(APIView):
    """
    Genera PDF de cotización de forma asíncrona usando Celery.
    Retorna task_id para que el frontend pueda consultar el estado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, quotation_id):
        """
        Inicia la generación asíncrona del PDF.

        Returns:
            {
                "task_id": "uuid-de-la-tarea",
                "message": "PDF generation started"
            }
        """
        try:
            # Verificar que la cotización existe
            Quotation.objects.get(id=quotation_id, deleted_at__isnull=True)
        except Quotation.DoesNotExist:
            return Response(
                {"error": "Cotización no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Lanzar tarea asíncrona
        task = generate_quotation_pdf.delay(quotation_id, request.user.id)

        logger.info(f"Task de generación de PDF iniciada: {task.id} para cotización {quotation_id}")

        return Response({
            "task_id": task.id,
            "message": "PDF generation started",
            "quotation_id": quotation_id
        }, status=status.HTTP_202_ACCEPTED)


class QuotationPDFStatusView(APIView):
    """
    Consulta el estado de una tarea de generación de PDF.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """
        Consulta el estado de la tarea.

        Returns:
            {
                "state": "PENDING|STARTED|SUCCESS|FAILURE",
                "result": "ruta/al/archivo.pdf" (si SUCCESS),
                "error": "mensaje de error" (si FAILURE)
            }
        """
        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        response_data = {
            "state": task.state,
            "task_id": task_id
        }

        if task.state == 'SUCCESS':
            response_data["result"] = task.result
            response_data["download_url"] = f"/media/{task.result}"
        elif task.state == 'FAILURE':
            response_data["error"] = str(task.info)

        return Response(response_data)