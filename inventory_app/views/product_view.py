# views/product_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser   # 👈 necesario
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer

def _is_admin(user):
    return getattr(user, "role", "") == "Administrator"

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.filter(deleted_at__isnull=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)               # 👈 acepta multipart

    def get_serializer_context(self):                            # 👈 pasa request
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        if not _is_admin(self.request.user):
            raise PermissionDenied("Only administrators can create products.")
        serializer.save()

class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)               # 👈 acepta multipart

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_update(self, serializer):
        if not _is_admin(self.request.user):
            raise PermissionDenied("Only administrators can update products.")
        serializer.save()
