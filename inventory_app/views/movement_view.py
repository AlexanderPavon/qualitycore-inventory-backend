# views/movement_view.py
import re
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from inventory_app.models.movement import Movement
from inventory_app.serializers.movement_serializer import MovementSerializer, MovementAdjustmentSerializer, MovementCorrectionSerializer
from inventory_app.constants import MovementType
from inventory_app.permissions import IsAdmin
from inventory_app.throttles import WriteThrottleMixin

class MovementListCreateView(WriteThrottleMixin, generics.ListCreateAPIView):
    """
    Vista para listar y crear movimientos con paginación y filtros server-side.

    Query params:
        type:   Filtra por tipo (adjustment, correction, input, output)
                Acepta múltiples valores separados por coma: type=adjustment,correction
        search: Búsqueda por nombre de producto, motivo o usuario
        page:   Número de página
    """
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Movement.objects.filter(deleted_at__isnull=True).select_related(
            'product',
            'user',
            'customer',
            'correction',
        ).order_by("-id")

        movement_type = self.request.query_params.get('type', '').strip()
        if movement_type:
            types = [t.strip() for t in movement_type.split(',') if t.strip()]
            qs = qs.filter(movement_type__in=types)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__date__gte=start_date)
        if end_date:
            qs = qs.filter(date__date__lte=end_date)

        search = self.request.query_params.get('search', '').strip()
        if search:
            q = (
                Q(product__name__icontains=search) |
                Q(reason__icontains=search) |
                Q(user__name__icontains=search)
            )
            purchase_match = re.fullmatch(r'compra\s*#\s*(\d+)', search, re.IGNORECASE)
            sale_match = re.fullmatch(r'venta\s*#\s*(\d+)', search, re.IGNORECASE)
            if purchase_match:
                q |= Q(purchase_id=int(purchase_match.group(1)))
            elif sale_match:
                q |= Q(sale_id=int(sale_match.group(1)))
            qs = qs.filter(q)

        return qs

    def create(self, request, *args, **kwargs):
        """
        Crea un movimiento de inventario.
        La lógica de negocio ahora se maneja en el MovementSerializer que delega a MovementService.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Pasar user de forma segura via save() — no se puede falsificar desde el cliente
        movement = serializer.save(user=request.user)

        # Mensaje apropiado según el tipo de movimiento
        movement_type = serializer.validated_data['movement_type']
        movement_type_text = "Entrada" if movement_type == MovementType.INPUT else "Salida"

        return Response({
            'message': f'{movement_type_text} registrada correctamente',
            'movement': MovementSerializer(movement).data
        }, status=status.HTTP_201_CREATED)


class AdjustmentCreateView(WriteThrottleMixin, generics.CreateAPIView):
    """
    POST /api/movements/adjustments/
    Crea un ajuste de inventario. Solo Admin y SuperAdmin.
    """
    serializer_class = MovementAdjustmentSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        movement = serializer.save(
            user=request.user,
            request=request,
        )

        return Response({
            'message': 'Ajuste de inventario registrado correctamente.',
            'movement': MovementSerializer(movement).data,
        }, status=status.HTTP_201_CREATED)


class CorrectionCreateView(WriteThrottleMixin, generics.CreateAPIView):
    """
    POST /api/movements/<pk>/correct/
    Corrige un movimiento existente (entrada o salida).
    Solo Admin y SuperAdmin.
    """
    serializer_class = MovementCorrectionSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        correction = serializer.save(
            user=request.user,
            original_movement_id=kwargs['pk'],
            request=request,
        )

        return Response({
            'message': 'Corrección registrada correctamente.',
            'movement': MovementSerializer(correction).data,
        }, status=status.HTTP_201_CREATED)
