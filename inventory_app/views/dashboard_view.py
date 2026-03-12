# views/dashboard_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from inventory_app.services import DashboardService
from inventory_app.services.dashboard_service import DASHBOARD_CACHE_KEY, DASHBOARD_CACHE_TTL


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # cache_page(60) cachea por URL + headers de sesión (una entrada por usuario).
        # Con una clave explícita compartimos la misma entrada para todos los usuarios,
        # reduciendo queries y espacio en caché.
        data = cache.get(DASHBOARD_CACHE_KEY)
        if data is None:
            data = DashboardService.get_summary()
            cache.set(DASHBOARD_CACHE_KEY, data, DASHBOARD_CACHE_TTL)
        return Response(data)
