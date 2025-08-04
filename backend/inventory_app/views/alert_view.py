# views/alert_view.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from inventory_app.models.alert import Alert
from inventory_app.serializers.alert_serializer import AlertSerializer

class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(deleted_at__isnull=True).order_by("-created_at")

class AlertUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk, deleted_at__isnull=True)
        except Alert.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        alert.deleted_at = timezone.now()
        alert.save()
        return Response({"message": "Alert successfully dismissed"})
