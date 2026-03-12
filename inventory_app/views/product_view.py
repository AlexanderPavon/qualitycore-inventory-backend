# views/product_view.py
from rest_framework import generics, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from inventory_app.constants import ProductStatus
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer
from inventory_app.permissions import IsAdminForWrite
from inventory_app.services import StockService


class ProductStockCheckView(APIView):
    """
    Verifica disponibilidad de stock para una lista de productos.
    Usado antes de confirmar una venta para avisar si el stock cambió.
    Delega la lógica a StockService.check_availability().
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data.get('items', [])
        if not items:
            return Response(
                {'detail': 'Se requiere una lista de items.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = StockService.check_availability(items)
        return Response(result)


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAdminForWrite]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'price', 'id']
    ordering = ['-id']  # default: más recientes primero

    def get_queryset(self):
        """
        Filtra productos activos por búsqueda de texto, categoría, proveedor y estado.
        Soporta los query params: ?search=, ?category=<id>, ?supplier=<id>, ?is_active=true|false
        """
        qs = Product.objects.filter(deleted_at__isnull=True).select_related(
            'category', 'supplier'
        ).order_by('-id')

        params = self.request.query_params
        if category := params.get('category'):
            ids = [int(c) for c in category.split(',') if c.strip().isdigit()]
            if ids:
                qs = qs.filter(category_id__in=ids)
        if supplier := params.get('supplier'):
            ids = [int(s) for s in supplier.split(',') if s.strip().isdigit()]
            if ids:
                qs = qs.filter(supplier_id__in=ids)
        is_active = params.get('is_active')
        if is_active is not None:
            status_value = ProductStatus.ACTIVE if is_active.lower() == 'true' else ProductStatus.INACTIVE
            qs = qs.filter(status=status_value)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.filter(deleted_at__isnull=True).select_related('category', 'supplier')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminForWrite]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
