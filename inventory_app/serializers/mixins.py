# serializers/mixins.py
import logging
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)


class TransactionSerializerMixin(serializers.Serializer):
    """
    Mixin compartido para SaleCreateSerializer y PurchaseCreateSerializer.
    Aplica el patrón Template Method: validate_items() y create() son idénticos;
    las subclases implementan get_transaction_label(), get_entity_id() y execute_service().
    """

    def get_transaction_label(self) -> str:
        """Nombre del tipo de transacción para el mensaje de error (ej. 'venta', 'compra')."""
        raise NotImplementedError

    def get_entity_id(self, validated_data: dict) -> int:
        """Extrae el ID de la entidad (customer_id o supplier_id) de validated_data."""
        raise NotImplementedError

    def execute_service(self, entity_id: int, user_id: int, items: list):
        """Llama al servicio correspondiente y retorna la instancia creada."""
        raise NotImplementedError

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                f"Debe incluir al menos un producto en la {self.get_transaction_label()}."
            )
        return value

    def create(self, validated_data):
        entity_id = self.get_entity_id(validated_data)
        items = validated_data.get('items')
        user_id = self.context.get('user_id')
        if not user_id:
            raise serializers.ValidationError("Usuario no identificado.")
        try:
            return self.execute_service(entity_id, user_id, items)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages if hasattr(e, 'messages') else str(e))


class InvoiceMovementsMixin:
    """
    Mixin compartido para SaleDetailSerializer y PurchaseDetailSerializer.
    Provee get_movements() que retorna los movimientos de una factura
    con datos de corrección inline.
    """
    MAX_MOVEMENTS = 100

    def get_movements(self, obj):
        total = (
            obj.movements
            .exclude(movement_type='correction')
            .count()
        )
        if total > self.MAX_MOVEMENTS:
            logger.warning(
                "Invoice %s id=%s has %d movements but only %d are returned "
                "(MAX_MOVEMENTS limit). Consider increasing the limit.",
                obj.__class__.__name__, obj.pk, total, self.MAX_MOVEMENTS,
            )
        movements = (
            obj.movements
            .select_related('product', 'correction')
            .exclude(movement_type='correction')
            .order_by('id')[:self.MAX_MOVEMENTS]
        )
        items = [{
            'id': m.id,
            'product_name': m.product.name,
            'quantity': m.quantity,
            'price': m.price,
            'subtotal': m.price * m.quantity,
            'corrected_by_id': m.correction_id,          # API name kept for backward compat
            'correction_quantity': m.correction.quantity if m.correction else None,
        } for m in movements]
        return {
            'items': items,
            'truncated': total > self.MAX_MOVEMENTS,
            'total': total,
        }
