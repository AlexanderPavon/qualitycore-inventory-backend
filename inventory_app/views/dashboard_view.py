# views/dashboard_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from inventory_app.models import Product, Customer, Movement, Quotation
from inventory_app.models.alert import Alert
from django.db.models import Count, Sum, Q

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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

        return Response(data)
