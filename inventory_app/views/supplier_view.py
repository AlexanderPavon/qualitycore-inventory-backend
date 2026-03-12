# views/supplier_view.py
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from inventory_app.models.supplier import Supplier
from inventory_app.serializers.supplier_serializer import SupplierSerializer
from inventory_app.permissions import IsAdminForWrite


class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminForWrite]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'email', 'tax_id', 'phone']
    ordering_fields = ['name', 'id']
    ordering = ['-id']


class SupplierDetailView(generics.RetrieveUpdateAPIView):
    queryset = Supplier.objects.filter(deleted_at__isnull=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminForWrite]
