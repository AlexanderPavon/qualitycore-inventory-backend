# views/dashboard_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from inventory_app.models import Product, Customer, Movement, Quotation
from inventory_app.models.alert import Alert  # <-- Importar modelo Alert
from django.db.models import Count, Sum, Q
from django.core.cache import cache

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Intentar obtener del caché (TTL: 5 minutos)
        cache_key = 'dashboard_summary'
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        # Si no está en caché, calcular
        total_products = Product.objects.filter(deleted_at__isnull=True).count()
        total_customers = Customer.objects.filter(deleted_at__isnull=True).count()
        movement_stats = Movement.objects.filter(deleted_at__isnull=True).aggregate(
            total=Count('id'),
            entries=Count('id', filter=Q(movement_type='input')),
            exits=Count('id', filter=Q(movement_type='output')),
            total_sales=Sum('quantity', filter=Q(movement_type='output'))
        )

        low_stock_alerts = Alert.objects.filter(deleted_at__isnull=True).count()

        data = {
            "total_products": total_products,
            "total_customers": total_customers,
            "total_movements": movement_stats['total'],
            "total_entries": movement_stats['entries'],
            "total_exits": movement_stats['exits'],
            "low_stock_alerts": low_stock_alerts,
            "total_sales": movement_stats['total_sales'] or 0
        }

        # Guardar en caché por 5 minutos (300 segundos)
        cache.set(cache_key, data, 300)

        return Response(data)
