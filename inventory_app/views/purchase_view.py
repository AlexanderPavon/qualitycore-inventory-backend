# views/purchase_view.py
from rest_framework import generics, status
from rest_framework.response import Response
from inventory_app.models import Purchase
from inventory_app.serializers.purchase_serializer import (
    PurchaseCreateSerializer,
    PurchaseDetailSerializer
)
from inventory_app.permissions import IsAdminForWrite


class PurchaseListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear compras.
    GET: Lista todas las compras
    POST: Crea una nueva compra con múltiples productos
    """
    queryset = Purchase.objects.filter(deleted_at__isnull=True).prefetch_related('movements__product')
    permission_classes = [IsAdminForWrite]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PurchaseCreateSerializer
        return PurchaseDetailSerializer

    def create(self, request, *args, **kwargs):
        # Pasar user_id al contexto del serializer
        serializer = self.get_serializer(
            data=request.data,
            context={'user_id': request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        # Retornar con el serializer de detalle
        detail_serializer = PurchaseDetailSerializer(purchase)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class PurchaseDetailView(generics.RetrieveAPIView):
    """
    Vista para obtener detalles de una compra específica.
    GET: Retorna detalles de una compra con todos sus movimientos
    """
    queryset = Purchase.objects.filter(deleted_at__isnull=True).prefetch_related('movements__product')
    serializer_class = PurchaseDetailSerializer
    permission_classes = [IsAdminForWrite]
