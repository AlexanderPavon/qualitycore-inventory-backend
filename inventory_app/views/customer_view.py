# views/customer_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from inventory_app.models.customer import Customer
from inventory_app.serializers.customer_serializer import CustomerSerializer
from inventory_app.constants import UserRole

class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role not in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN, UserRole.USER]:
            raise PermissionDenied("Only administrators can create customers.")
        serializer.save()

class CustomerDetailView(generics.RetrieveUpdateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        if self.request.user.role not in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN, UserRole.USER]:
            raise PermissionDenied("Only administrators can update customers.")
        serializer.save()
