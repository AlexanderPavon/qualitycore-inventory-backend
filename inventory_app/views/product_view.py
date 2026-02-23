# views/product_view.py
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from inventory_app.models.product import Product
from inventory_app.serializers.product_serializer import ProductSerializer
from inventory_app.permissions import IsAdminForWrite


class ProductStockCheckView(APIView):
    """
    Verifica disponibilidad de stock para una lista de productos.
    Usado antes de confirmar una venta para avisar si el stock cambió.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data.get('items', [])
        if not items:
            return Response(
                {'detail': 'Se requiere una lista de items.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        unavailable = []
        for item in items:
            product_id = item.get('product')
            requested = item.get('quantity', 0)
            try:
                product = Product.objects.get(id=product_id, deleted_at__isnull=True)
                if requested > product.current_stock:
                    unavailable.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'requested': requested,
                        'available': product.current_stock,
                    })
            except Product.DoesNotExist:
                unavailable.append({
                    'product_id': product_id,
                    'product_name': 'Producto no encontrado',
                    'requested': requested,
                    'available': 0,
                })

        return Response({
            'all_available': len(unavailable) == 0,
            'unavailable': unavailable,
        })


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
    queryset = Product.objects.select_related('category', 'supplier').all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminForWrite]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
