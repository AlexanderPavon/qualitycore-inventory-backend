# views/customer_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from inventory_app.models.customer import Customer
from inventory_app.serializers.customer_serializer import CustomerSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class CustomerDetailView(generics.RetrieveUpdateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
