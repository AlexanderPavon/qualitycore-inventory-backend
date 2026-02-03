# views/product_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer
from inventory_app.constants import UserRole

def _is_admin(user):
    return getattr(user, "role", "") in [UserRole.ADMINISTRATOR, UserRole.SUPER_ADMIN]

class ProductListCreateView(generics.ListCreateAPIView):
    # Optimización: select_related para evitar N+1 queries
    queryset = Product.objects.filter(deleted_at__isnull=True).select_related(
        'category',
        'supplier'
    ).order_by('-id')  # Ordenar por ID descendente (más recientes primero)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)   # 👈 acepta multipart y JSON

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
    parser_classes = (MultiPartParser, FormParser, JSONParser)   # 👈 acepta multipart y JSON

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_update(self, serializer):
        if not _is_admin(self.request.user):
            raise PermissionDenied("Only administrators can update products.")
        serializer.save()
