# views/supplier_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from inventory_app.models.supplier import Supplier
from inventory_app.serializers.supplier_serializer import SupplierSerializer

class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.filter(deleted_at__isnull=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role != "Administrator":
            raise PermissionDenied("Only administrators can create suppliers.")
        serializer.save()

class SupplierDetailView(generics.RetrieveUpdateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        if self.request.user.role != "Administrator":
            raise PermissionDenied("Only administrators can update suppliers.")
        serializer.save()
