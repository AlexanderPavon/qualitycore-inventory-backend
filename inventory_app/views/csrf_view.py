# inventory_app/views/csrf_view.py
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
@ensure_csrf_cookie
def csrf_ready(request): return JsonResponse({"detail":"ok"})
