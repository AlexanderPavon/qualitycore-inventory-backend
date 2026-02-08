# views/category_view.py
from rest_framework import generics
from inventory_app.models.category import Category
from inventory_app.serializers.category_serializer import CategorySerializer
from inventory_app.permissions import IsAdminForWrite


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('-id')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminForWrite]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminForWrite]
