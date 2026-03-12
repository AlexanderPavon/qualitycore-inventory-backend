# views/customer_view.py
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from inventory_app.models.customer import Customer
from inventory_app.serializers.customer_serializer import CustomerSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'email', 'document', 'phone']
    ordering_fields = ['name', 'id']
    ordering = ['-id']


class CustomerDetailView(generics.RetrieveUpdateAPIView):
    queryset = Customer.objects.filter(deleted_at__isnull=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
