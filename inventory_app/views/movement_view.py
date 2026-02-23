# views/movement_view.py
import logging
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.movement import Movement
from inventory_app.serializers.movement_serializer import MovementSerializer, AdjustmentMovementSerializer, CorrectionSerializer
from inventory_app.constants import MovementType
from inventory_app.permissions import IsAdmin
from inventory_app.throttles import WriteOperationThrottle

logger = logging.getLogger(__name__)

class MovementListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear movimientos con paginación y filtros server-side.

    Query params:
        type: Filtra por tipo (adjustment, correction, input, output)
              Acepta múltiples valores separados por coma: type=adjustment,correction
        page: Número de página
    """
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [WriteOperationThrottle]

    def get_queryset(self):
        qs = Movement.objects.filter(deleted_at__isnull=True).select_related(
            'product',
            'user',
            'customer',
            'corrected_by',
        ).order_by("-id")

        movement_type = self.request.query_params.get('type', '').strip()
        if movement_type:
            types = [t.strip() for t in movement_type.split(',') if t.strip()]
            qs = qs.filter(movement_type__in=types)

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


class AdjustmentCreateView(generics.CreateAPIView):
    """
    POST /api/movements/adjustments/
    Crea un ajuste de inventario. Solo Admin y SuperAdmin.
    """
    serializer_class = AdjustmentMovementSerializer
    permission_classes = [IsAdmin]
    throttle_classes = [WriteOperationThrottle]

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


class CorrectionCreateView(generics.CreateAPIView):
    """
    POST /api/movements/<pk>/correct/
    Corrige un movimiento existente (entrada o salida).
    Solo Admin y SuperAdmin.
    """
    serializer_class = CorrectionSerializer
    permission_classes = [IsAdmin]
    throttle_classes = [WriteOperationThrottle]

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
