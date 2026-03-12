# views/category_view.py
from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from inventory_app.models.category import Category
from inventory_app.serializers.category_serializer import CategorySerializer
from inventory_app.permissions import IsAdminForWrite


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('-id')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminForWrite]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['-id']


class CategoryDetailView(generics.RetrieveUpdateAPIView):
    """
    Solo PATCH (no HTTP DELETE).
    La eliminación se realiza via PATCH con deleted_at, igual que Customer/Supplier.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminForWrite]
