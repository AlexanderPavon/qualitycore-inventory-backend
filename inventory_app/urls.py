from django.urls import path

from inventory_app.views.auth_view import (
    LoginView, ForgotPasswordView, ResetPasswordView, ChangePasswordView
)
from inventory_app.views.user_view import UserListCreateView, UserDetailView
from inventory_app.views.customer_view import CustomerListCreateView, CustomerDetailView
from inventory_app.views.supplier_view import SupplierListCreateView, SupplierDetailView
from inventory_app.views.product_view import ProductListCreateView, ProductDetailView
from inventory_app.views.category_view import CategoryListCreateView, CategoryDetailView
from inventory_app.views.movement_view import MovementListCreateView
from inventory_app.views.report_view import ReportListView, ReportGeneratePDFView
from inventory_app.views.dashboard_view import DashboardSummaryView

from inventory_app.views.quotation_view import (
    QuotationCreateView, QuotationListView, QuotationDetailView, QuotationPDFView
)

from inventory_app.views.alert_view import AlertListView, AlertUpdateView

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view()),
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

    # Categories
    path('categories/', CategoryListCreateView.as_view()),
    path('categories/<int:pk>/', CategoryDetailView.as_view()),

    # Movements
    path('movements/', MovementListCreateView.as_view()),

    # Reports
    path('reports/', ReportListView.as_view()),
    path('reports/generate/', ReportGeneratePDFView.as_view()),


    # Quotations
    path('quotations/', QuotationListView.as_view()),
    path('quotations/<int:pk>/', QuotationDetailView.as_view()),
    path('quotations/create/', QuotationCreateView.as_view()),
    path('quotations/pdf/<int:quotation_id>/', QuotationPDFView.as_view()),


    # Alerts
    path('alerts/', AlertListView.as_view()),
    path('alerts/<int:pk>/dismiss/', AlertUpdateView.as_view()),

    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view()),
]
