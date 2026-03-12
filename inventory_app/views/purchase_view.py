# views/purchase_view.py
import re
from rest_framework import generics, status
from rest_framework.response import Response
from django.db.models import Q
from inventory_app.models import Purchase
from inventory_app.serializers.purchase_serializer import (
    PurchaseCreateSerializer,
    PurchaseDetailSerializer
)
from inventory_app.permissions import IsAdminForWrite
from inventory_app.throttles import WriteThrottleMixin
from inventory_app.views.list_mixins import IdempotentCreateMixin, NoPageMixin


class PurchaseListCreateView(WriteThrottleMixin, IdempotentCreateMixin, NoPageMixin, generics.ListCreateAPIView):
    idempotency_prefix = "purchase"
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

    def get_queryset(self):
        qs = Purchase.objects.filter(deleted_at__isnull=True).select_related(
            'supplier',
            'user'
        ).prefetch_related('movements__product').order_by("-date")

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        search = self.request.query_params.get('search', '').strip()
        if start_date:
            qs = qs.filter(date__date__gte=start_date)
        if end_date:
            qs = qs.filter(date__date__lte=end_date)
        if search:
            q = (
                Q(supplier__name__icontains=search) |
                Q(user__name__icontains=search) |
                Q(movements__product__name__icontains=search)
            )
            id_match = re.fullmatch(r'(?:compra\s*#\s*)?(\d+)', search, re.IGNORECASE)
            if id_match:
                q |= Q(id=int(id_match.group(1)))
            qs = qs.filter(q).distinct()

        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PurchaseCreateSerializer
        return PurchaseDetailSerializer

    def _do_create(self, request, *args, **kwargs):
        """Crea una compra con múltiples productos delegando a PurchaseService vía serializer."""
        serializer = self.get_serializer(
            data=request.data,
            context={'user_id': request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        detail_serializer = PurchaseDetailSerializer(purchase)
        return Response(
            {'message': 'Compra registrada correctamente', 'purchase': detail_serializer.data},
            status=status.HTTP_201_CREATED,
        )


class PurchaseDetailView(generics.RetrieveAPIView):
    """
    Vista para obtener detalles de una compra específica.
    GET: Retorna detalles de una compra con todos sus movimientos
    """
    queryset = Purchase.objects.filter(deleted_at__isnull=True).prefetch_related('movements__product')
    serializer_class = PurchaseDetailSerializer
    permission_classes = [IsAdminForWrite]
