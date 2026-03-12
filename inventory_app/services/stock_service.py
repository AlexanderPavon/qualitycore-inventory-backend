# services/stock_service.py
"""
Servicio para verificar disponibilidad de stock de múltiples productos.
Centraliza la regla "stock >= cantidad solicitada" en un solo lugar,
usada por ProductStockCheckView (pre-flight check del frontend) y
cualquier otro consumer que necesite el resultado como lista (no excepción).
"""
from inventory_app.models.product import Product


class StockService:
    @staticmethod
    def check_availability(items: list) -> dict:
        """
        Verifica disponibilidad de stock para una lista de items.

        Args:
            items: Lista de dicts con keys 'product' (ID) y 'quantity'.

        Returns:
            {
                'all_available': bool,
                'unavailable': [
                    {'product_id': int, 'product_name': str, 'requested': int, 'available': int}
                ]
            }
        """
        if not items:
            return {'all_available': True, 'unavailable': []}

        product_ids = [item.get('product') for item in items]
        stock_map = {
            p.id: p
            for p in Product.objects.filter(
                id__in=product_ids, deleted_at__isnull=True
            ).only('id', 'name', 'current_stock')
        }

        unavailable = []
        for item in items:
            product_id = item.get('product')
            requested = item.get('quantity', 0)
            product = stock_map.get(product_id)

            if product is None:
                unavailable.append({
                    'product_id': product_id,
                    'product_name': 'Producto no encontrado',
                    'requested': requested,
                    'available': 0,
                })
            elif requested > product.current_stock:
                unavailable.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'requested': requested,
                    'available': product.current_stock,
                })

        return {'all_available': len(unavailable) == 0, 'unavailable': unavailable}
