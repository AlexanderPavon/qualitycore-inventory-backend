# services/alert_service.py
"""
Servicio centralizado para gestionar alertas de stock bajo.
Evita duplicación de código y garantiza consistencia en tipos de alertas.
"""

import logging
from django.utils import timezone
from inventory_app.models.alert import Alert
from inventory_app.models.product import Product

logger = logging.getLogger(__name__)


class AlertService:
    """
    Servicio para gestionar alertas de stock de productos.
    Centraliza la lógica de creación, actualización y eliminación de alertas.
    """

    # Tipos de alertas (constantes para evitar magic strings)
    ALERT_TYPE_OUT_OF_STOCK = "out_of_stock"
    ALERT_TYPE_ONE_UNIT = "one_unit"
    ALERT_TYPE_LOW_STOCK = "low_stock"

    @staticmethod
    def update_stock_alerts(product: Product) -> None:
        """
        Actualiza las alertas de stock para un producto según su nivel actual.

        - Si el stock está por encima del mínimo: elimina todas las alertas
        - Si el stock es 0: crea alerta "out_of_stock"
        - Si el stock es 1: crea alerta "one_unit"
        - Si el stock está por debajo del mínimo: crea alerta "low_stock"

        Args:
            product: Instancia del producto a evaluar

        Returns:
            None
        """
        # Si el stock está por encima del mínimo, eliminar todas las alertas previas
        if product.current_stock > product.minimum_stock:
            deleted_count = product.alerts.filter(deleted_at__isnull=True).update(
                deleted_at=timezone.now()
            )
            if deleted_count > 0:
                logger.debug(f"Eliminadas {deleted_count} alertas de {product.name} (stock OK)")
            return

        # Determinar el tipo de alerta y mensaje según el nivel de stock
        if product.current_stock == 0:
            alert_type = AlertService.ALERT_TYPE_OUT_OF_STOCK
            message = f"El producto '{product.name}' está agotado."
        elif product.current_stock == 1:
            alert_type = AlertService.ALERT_TYPE_ONE_UNIT
            message = f"Solo queda 1 unidad del producto '{product.name}'."
        else:
            alert_type = AlertService.ALERT_TYPE_LOW_STOCK
            message = (
                f"El producto '{product.name}' está por debajo del stock mínimo "
                f"({product.minimum_stock}). Stock actual: {product.current_stock}"
            )

        # Verificar si ya existe una alerta activa del mismo tipo
        existing_alert = product.alerts.filter(
            deleted_at__isnull=True,
            type=alert_type
        ).exists()

        if not existing_alert:
            # Eliminar alertas anteriores de otros tipos (para cambiar de tipo si es necesario)
            product.alerts.filter(deleted_at__isnull=True).exclude(
                type=alert_type
            ).update(deleted_at=timezone.now())

            # Crear la nueva alerta
            Alert.objects.create(
                product=product,
                type=alert_type,
                message=message
            )
            logger.info(f"Alerta creada: {alert_type} para producto '{product.name}' (stock: {product.current_stock})")
        else:
            logger.debug(f"Alerta {alert_type} ya existe para {product.name}")
