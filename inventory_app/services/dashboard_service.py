# services/dashboard_service.py
"""
Lógica de negocio del dashboard.
Centraliza las queries del resumen para que sean testables e independientes
de la capa HTTP (views).
"""
from django.db.models import Count, Sum, Q
from inventory_app.models import Product, Customer, Movement
from inventory_app.models.alert import Alert

# Clave y TTL compartidos entre todos los módulos que leen o invalidan el caché
# del dashboard. Definidos aquí (única fuente de verdad) para que cambiar el
# nombre o el TTL en un solo lugar sea suficiente.
DASHBOARD_CACHE_KEY = 'dashboard:summary'
DASHBOARD_CACHE_TTL = 60  # segundos


class DashboardService:
    @staticmethod
    def get_summary() -> dict:
        """
        Devuelve el resumen de indicadores del dashboard en una sola llamada.
        Usa aggregate() para consolidar las queries de Movement en un solo hit a BD.
        """
        total_products = Product.objects.filter(deleted_at__isnull=True).count()
        total_customers = Customer.objects.filter(deleted_at__isnull=True).count()

        movement_stats = Movement.objects.filter(deleted_at__isnull=True).aggregate(
            total=Count('id'),
            entries=Count('id', filter=Q(movement_type='input')),
            exits=Count('id', filter=Q(movement_type='output')),
            total_sales=Sum('quantity', filter=Q(movement_type='output')),
        )

        low_stock_alerts = Alert.objects.filter(deleted_at__isnull=True).count()

        return {
            "total_products": total_products,
            "total_customers": total_customers,
            "total_movements": movement_stats['total'],
            "total_entries": movement_stats['entries'],
            "total_exits": movement_stats['exits'],
            "low_stock_alerts": low_stock_alerts,
            "total_sales": movement_stats['total_sales'] or 0,
        }
