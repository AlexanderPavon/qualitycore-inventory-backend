# views/sale_view.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.sale import Sale
from inventory_app.serializers.sale_serializer import SaleCreateSerializer, SaleDetailSerializer

class SaleListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear ventas.
    GET: Lista todas las ventas
    POST: Crea una nueva venta con múltiples productos
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optimización: select_related para evitar N+1 queries al serializar.
        """
        return Sale.objects.filter(deleted_at__isnull=True).select_related(
            'customer',
            'user'
        ).prefetch_related('movements__product').order_by("-date")

    def get_serializer_class(self):
        """
        Usar diferentes serializers para lista y creación.
        """
        if self.request.method == 'POST':
            return SaleCreateSerializer
        return SaleDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Crea una venta con múltiples productos.
        La lógica de negocio se maneja en el SaleSerializer que delega a SaleService.
        """
        # Pasar el user_id al serializer a través del contexto
        serializer = self.get_serializer(
            data=request.data,
            context={'user_id': request.user.id}
        )
        serializer.is_valid(raise_exception=True)

        # El serializer delega la creación a SaleService
        sale = serializer.save()

        # Retornar respuesta con detalles completos
        detail_serializer = SaleDetailSerializer(sale)

        return Response({
            'message': 'Venta registrada correctamente',
            'sale': detail_serializer.data
        }, status=status.HTTP_201_CREATED)


class SaleDetailView(generics.RetrieveAPIView):
    """
    Vista para ver detalles de una venta específica.
    """
    queryset = Sale.objects.filter(deleted_at__isnull=True).select_related(
        'customer',
        'user'
    ).prefetch_related('movements__product')
    serializer_class = SaleDetailSerializer
    permission_classes = [IsAuthenticated]
