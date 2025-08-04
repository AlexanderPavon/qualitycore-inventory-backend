# views/dashboard_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from inventory_app.models import Product, Customer, Movement, Quotation
from inventory_app.models.alert import Alert  # <-- Importar modelo Alert
from django.db.models import Sum, F

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_products = Product.objects.filter(deleted_at__isnull=True).count()
        total_customers = Customer.objects.filter(deleted_at__isnull=True).count()
        total_movements = Movement.objects.filter(deleted_at__isnull=True).count()
        total_entries = Movement.objects.filter(movement_type="input", deleted_at__isnull=True).count()
        total_exits = Movement.objects.filter(movement_type="output", deleted_at__isnull=True).count()

        # ✅ Solo contar alertas activas (no eliminadas)
        low_stock_alerts = Alert.objects.filter(deleted_at__isnull=True).count()

        total_sales = Movement.objects.filter(
            movement_type="output",
            deleted_at__isnull=True
        ).aggregate(total=Sum("quantity"))["total"] or 0

        return Response({
            "total_products": total_products,
            "total_customers": total_customers,
            "total_movements": total_movements,
            "total_entries": total_entries,
            "total_exits": total_exits,
            "low_stock_alerts": low_stock_alerts,
            "total_sales": total_sales
        })
