# views/sale_view.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.sale import Sale
from inventory_app.serializers.sale_serializer import SaleCreateSerializer, SaleDetailSerializer
from inventory_app.throttles import WriteOperationThrottle

class SaleListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear ventas con paginación y filtros server-side.
    GET: Lista ventas paginadas (20 por página por defecto)
    POST: Crea una nueva venta con múltiples productos

    Query params:
        search: Filtra por nombre de cliente o usuario
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)
        page: Número de página
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [WriteOperationThrottle]

    def get_queryset(self):
        qs = Sale.objects.filter(deleted_at__isnull=True).select_related(
            'customer',
            'user'
        ).prefetch_related('movements__product').order_by("-date")

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__date__gte=start_date)
        if end_date:
            qs = qs.filter(date__date__lte=end_date)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Sin paginación cuando se busca (client-side filtering necesita todos los registros)
        if request.query_params.get('no_page') == 'true':
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            })

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
