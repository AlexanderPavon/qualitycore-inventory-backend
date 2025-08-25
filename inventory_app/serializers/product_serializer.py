# serializers/product_serializer.py
from rest_framework import serializers
from inventory_app.models.product import Product

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'  # mantiene todos los campos del modelo
        extra_kwargs = {
            "image": {"write_only": True, "required": False}  # se puede subir pero no es obligatorio
        }

    def get_image_url(self, obj):
        # Con Cloudinary activo, obj.image.url es la URL pública
        return obj.image.url if getattr(obj, "image", None) else None
