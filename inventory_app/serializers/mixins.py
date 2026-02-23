# serializers/mixins.py


class InvoiceMovementsMixin:
    """
    Mixin compartido para SaleDetailSerializer y PurchaseDetailSerializer.
    Provee get_movements() que retorna los movimientos de una factura
    con datos de corrección inline.
    """
    MAX_MOVEMENTS = 100

    def get_movements(self, obj):
        movements = (
            obj.movements
            .select_related('product', 'corrected_by')
            .exclude(movement_type='correction')
            .order_by('id')[:self.MAX_MOVEMENTS]
        )
        return [{
            'id': m.id,
            'product_name': m.product.name,
            'quantity': m.quantity,
            'price': m.price,
            'subtotal': m.price * m.quantity,
            'corrected_by_id': m.corrected_by_id,
            'correction_quantity': m.corrected_by.quantity if m.corrected_by else None,
        } for m in movements]
