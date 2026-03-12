# views/sale_view.py
import re
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from inventory_app.models.sale import Sale
from inventory_app.serializers.sale_serializer import SaleCreateSerializer, SaleDetailSerializer
from inventory_app.throttles import WriteThrottleMixin
from inventory_app.views.list_mixins import IdempotentCreateMixin, NoPageMixin

class SaleListCreateView(WriteThrottleMixin, IdempotentCreateMixin, NoPageMixin, generics.ListCreateAPIView):
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
    idempotency_prefix = "sale"
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Sale.objects.filter(deleted_at__isnull=True).select_related(
            'customer',
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
                Q(customer__name__icontains=search) |
                Q(user__name__icontains=search) |
                Q(movements__product__name__icontains=search)
            )
            id_match = re.fullmatch(r'(?:venta\s*#\s*)?(\d+)', search, re.IGNORECASE)
            if id_match:
                q |= Q(id=int(id_match.group(1)))
            qs = qs.filter(q).distinct()

        return qs

    def get_serializer_class(self):
        """
        Usar diferentes serializers para lista y creación.
        """
        if self.request.method == 'POST':
            return SaleCreateSerializer
        return SaleDetailSerializer

    def _do_create(self, request, *args, **kwargs):
        """Crea una venta con múltiples productos delegando a SaleService vía serializer."""
        serializer = self.get_serializer(
            data=request.data,
            context={'user_id': request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()

        detail_serializer = SaleDetailSerializer(sale)
        return Response(
            {'message': 'Venta registrada correctamente', 'sale': detail_serializer.data},
            status=status.HTTP_201_CREATED,
        )


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
