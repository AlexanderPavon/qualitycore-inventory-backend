# views/product_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.filter(deleted_at__isnull=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role != "Administrator":
            raise PermissionDenied("Only administrators can create products.")
        serializer.save()

class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        if self.request.user.role != "Administrator":
            raise PermissionDenied("Only administrators can update products.")
        serializer.save()