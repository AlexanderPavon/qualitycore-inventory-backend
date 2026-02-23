# serializers/category_serializer.py
from rest_framework import serializers
from inventory_app.models.category import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value, deleted_at__isnull=True)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una categoría con este nombre.')
        return value
