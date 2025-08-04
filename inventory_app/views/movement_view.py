# views/movement_view.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from inventory_app.models.movement import Movement
from inventory_app.serializers.movement_serializer import MovementSerializer
from inventory_app.models.alert import Alert
from django.utils import timezone

class MovementListCreateView(generics.ListCreateAPIView):
    queryset = Movement.objects.filter(deleted_at__isnull=True).order_by("-id")
    serializer_class = MovementSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role not in ['Administrator', 'User']:
            raise PermissionDenied("You do not have permission to register movements.")

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        movement_type = serializer.validated_data['movement_type'].lower()

        if movement_type == "output" and quantity > product.current_stock:
            raise ValidationError("Insufficient stock for this output.")

        if movement_type == "input":
            product.current_stock += quantity
        elif movement_type == "output":
            product.current_stock -= quantity

        movement = serializer.save(
            user=self.request.user,
            stock_in_movement=product.current_stock
        )

        if product.current_stock <= product.minimum_stock:
            alert_type = "low_stock"
            message = f"⚠️ El producto '{product.name}' está por debajo del stock mínimo ({product.minimum_stock})."


            if product.current_stock == 1:
                alert_type = "one_left"
                message = f"⚠️ Solo queda 1 unidad del producto '{product.name}'."

            elif product.current_stock == 0:
                alert_type = "out_of_stock"
                message = f"🚨 El producto'{product.name}' esta agotado."

            exists = product.alerts.filter(deleted_at__isnull=True, type=alert_type).exists()
            if not exists:
                Alert.objects.create(
                    product=product,
                    type=alert_type,
                    message=message
                )

        product.save()
