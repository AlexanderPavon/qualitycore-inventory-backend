from django.urls import path
from inventory_app.views.auth_view import (
    LoginView, ForgotPasswordView, ResetPasswordView, ChangePasswordView, LogoutView
)
from inventory_app.views.token_refresh_view import CookieTokenRefreshView
from inventory_app.views.user_view import UserListCreateView, UserDetailView
from inventory_app.views.customer_view import CustomerListCreateView, CustomerDetailView
from inventory_app.views.supplier_view import SupplierListCreateView, SupplierDetailView
from inventory_app.views.product_view import ProductListCreateView, ProductDetailView, ProductStockCheckView
from inventory_app.views.category_view import CategoryListCreateView, CategoryDetailView
from inventory_app.views.movement_view import MovementListCreateView, AdjustmentCreateView, CorrectionCreateView
from inventory_app.views.sale_view import SaleListCreateView, SaleDetailView
from inventory_app.views.purchase_view import PurchaseListCreateView, PurchaseDetailView
from inventory_app.views.report_view import ReportListView, ReportGeneratePDFView, ReportDownloadView, ReportStatusView
from inventory_app.views.dashboard_view import DashboardSummaryView

from inventory_app.views.quotation_view import (
    QuotationCreateView, QuotationListView, QuotationDetailView,
    QuotationPDFView, QuotationPDFStatusView
)

from inventory_app.views.alert_view import AlertListView, AlertUpdateView
from inventory_app.views.config_view import ConfigView

from inventory_app.views.csrf_view import csrf_ready
from inventory_app.views.health_view import health_check
urlpatterns = [
    # Auth
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),

    # Users
    path('users/', UserListCreateView.as_view()),
    path('users/<int:pk>/', UserDetailView.as_view()),

    # Customers
    path('customers/', CustomerListCreateView.as_view()),
    path('customers/<int:pk>/', CustomerDetailView.as_view()),

    # Suppliers
    path('suppliers/', SupplierListCreateView.as_view()),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view()),

    # Products
    path('products/', ProductListCreateView.as_view()),
    path('products/<int:pk>/', ProductDetailView.as_view()),
    path('products/check-stock/', ProductStockCheckView.as_view()),

    # Categories
    path('categories/', CategoryListCreateView.as_view()),
    path('categories/<int:pk>/', CategoryDetailView.as_view()),

    # Movements
    path('movements/', MovementListCreateView.as_view()),
    path('movements/adjustments/', AdjustmentCreateView.as_view()),
    path('movements/<int:pk>/correct/', CorrectionCreateView.as_view()),

    # Sales
    path('sales/', SaleListCreateView.as_view()),
    path('sales/<int:pk>/', SaleDetailView.as_view()),

    # Purchases
    path('purchases/', PurchaseListCreateView.as_view()),
    path('purchases/<int:pk>/', PurchaseDetailView.as_view()),

    # Reports
    path('reports/', ReportListView.as_view()),
    path('reports/generate/', ReportGeneratePDFView.as_view()),
    path('reports/status/<str:task_id>/', ReportStatusView.as_view()),
    path('reports/download/<int:pk>/', ReportDownloadView.as_view(), name='report-download'),

    # Quotations
    path('quotations/', QuotationListView.as_view()),
    path('quotations/<int:pk>/', QuotationDetailView.as_view()),
    path('quotations/create/', QuotationCreateView.as_view()),
    path('quotations/pdf/<int:quotation_id>/', QuotationPDFView.as_view()),
    path('quotations/pdf/status/<str:task_id>/', QuotationPDFStatusView.as_view()),


    # Alerts
    path('alerts/', AlertListView.as_view()),
    path('alerts/<int:pk>/dismiss/', AlertUpdateView.as_view()),

    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view()),

    # Config (constantes del sistema)
    path('config/', ConfigView.as_view()),

    path('csrf/', csrf_ready),

    # Health check (para orquestadores como Railway, Docker, etc.)
    path('health/', health_check),
]
