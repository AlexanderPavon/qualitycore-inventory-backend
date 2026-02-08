# views/movement_view.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory_app.models.movement import Movement
from inventory_app.serializers.movement_serializer import MovementSerializer
from inventory_app.constants import MovementType

class MovementListCreateView(generics.ListCreateAPIView):
    # Optimización: select_related para evitar N+1 queries al serializar
    queryset = Movement.objects.filter(deleted_at__isnull=True).select_related(
        'product',
        'user',
        'customer'
    ).order_by("-id")
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Crea un movimiento de inventario.
        La lógica de negocio ahora se maneja en el MovementSerializer que delega a MovementService.
        """
        # Agregar el usuario autenticado al request data
        data = request.data.copy()
        data['user'] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # El serializer delega la creación a MovementService
        movement = serializer.save()

        # Mensaje apropiado según el tipo de movimiento
        movement_type = serializer.validated_data['movement_type']
        movement_type_text = "Entrada" if movement_type == MovementType.INPUT else "Salida"

        return Response({
            'message': f'{movement_type_text} registrada correctamente',
            'movement': MovementSerializer(movement).data
        }, status=status.HTTP_201_CREATED)
