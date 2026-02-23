# views/report_view.py
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.report import Report
from inventory_app.serializers.report_serializer import ReportSerializer
from inventory_app.tasks import generate_report_pdf
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from pathlib import Path
import logging

TASK_OWNER_TIMEOUT = 3600  # 1 hora, igual que CELERY_RESULT_EXPIRES

logger = logging.getLogger(__name__)

class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk, deleted_at__isnull=True)
        # opcional: limitar al dueño o admin
        # if report.user != request.user and getattr(request.user, "role", "") != UserRole.ADMINISTRATOR:
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
        return Report.objects.filter(user=self.request.user, deleted_at__isnull=True).order_by("-generated_at")


class ReportGeneratePDFView(APIView):
    """Inicia generación asíncrona de PDF con Celery."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        report_type = request.data.get("type", "movimientos")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        # Validar fechas antes de despachar la tarea
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return Response({"detail": "Fecha de inicio inválida"}, status=status.HTTP_400_BAD_REQUEST)
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return Response({"detail": "Fecha de fin inválida"}, status=status.HTTP_400_BAD_REQUEST)

        # Despachar tarea asíncrona
        task = generate_report_pdf.delay(
            request.user.id, report_type, start_date, end_date
        )

        # Registrar ownership: solo el creador puede consultar el estado
        cache.set(f"task_owner:{task.id}", request.user.id, timeout=TASK_OWNER_TIMEOUT)

        logger.info(f"Tarea de generación de reporte iniciada: {task.id} tipo={report_type}")

        return Response({
            "task_id": task.id,
            "message": "Generando reporte...",
        })


class ReportStatusView(APIView):
    """Consulta el estado de una tarea de generación de PDF."""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        # Validar ownership
        owner_id = cache.get(f"task_owner:{task_id}")
        if owner_id is None or owner_id != request.user.id:
            return Response(
                {"detail": "Tarea no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        response_data = {
            "state": task.state,
            "task_id": task_id,
        }

        if task.state == 'SUCCESS':
            response_data["result"] = task.result
            response_data["download_url"] = f"/media/{task.result}"
        elif task.state == 'FAILURE':
            response_data["error"] = str(task.info)

        return Response(response_data)