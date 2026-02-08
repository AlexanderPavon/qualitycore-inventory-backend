# views/product_view.py
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer
from inventory_app.permissions import IsAdminForWrite


class ProductListCreateView(generics.ListCreateAPIView):
    # Optimización: select_related para evitar N+1 queries
    queryset = Product.objects.filter(deleted_at__isnull=True).select_related(
        'category',
        'supplier'
    ).order_by('-id')  # Ordenar por ID descendente (más recientes primero)
    serializer_class = ProductSerializer
    permission_classes = [IsAdminForWrite]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminForWrite]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
