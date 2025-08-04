# serializers/category_serializer.py
from rest_framework import serializers
from inventory_app.models.category import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
