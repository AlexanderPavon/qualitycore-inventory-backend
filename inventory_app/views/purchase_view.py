# views/purchase_view.py
from rest_framework import generics, status
from rest_framework.response import Response
from inventory_app.models import Purchase
from inventory_app.serializers.purchase_serializer import (
    PurchaseCreateSerializer,
    PurchaseDetailSerializer
)
from inventory_app.permissions import IsAdminForWrite
from inventory_app.throttles import WriteOperationThrottle


class PurchaseListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear compras con paginación y filtros server-side.
    GET: Lista compras paginadas (20 por página por defecto)
    POST: Crea una nueva compra con múltiples productos

    Query params:
        search: Filtra por nombre de proveedor o usuario
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)
        page: Número de página
    """
    permission_classes = [IsAdminForWrite]
    throttle_classes = [WriteOperationThrottle]

    def get_queryset(self):
        qs = Purchase.objects.filter(deleted_at__isnull=True).select_related(
            'supplier',
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
        if self.request.method == 'POST':
            return PurchaseCreateSerializer
        return PurchaseDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Crea una compra con múltiples productos.
        La lógica de negocio se maneja en el PurchaseSerializer que delega a PurchaseService.
        """
        # Pasar user_id al contexto del serializer
        serializer = self.get_serializer(
            data=request.data,
            context={'user_id': request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        # Retornar respuesta con detalles completos
        detail_serializer = PurchaseDetailSerializer(purchase)
        return Response({
            'message': 'Compra registrada correctamente',
            'purchase': detail_serializer.data
        }, status=status.HTTP_201_CREATED)


class PurchaseDetailView(generics.RetrieveAPIView):
    """
    Vista para obtener detalles de una compra específica.
    GET: Retorna detalles de una compra con todos sus movimientos
    """
    queryset = Purchase.objects.filter(deleted_at__isnull=True).prefetch_related('movements__product')
    serializer_class = PurchaseDetailSerializer
    permission_classes = [IsAdminForWrite]
