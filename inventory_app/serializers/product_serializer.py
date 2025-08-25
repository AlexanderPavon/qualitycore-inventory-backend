# serializers/product_serializer.py
from rest_framework import serializers
from inventory_app.models.product import Product

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            "image": {"write_only": True, "required": False}
        }

    def get_image_url(self, obj):
        if not obj.image:
            return None
            
        try:
            url = obj.image.url
            
            # Solo devolver URLs de Cloudinary válidas
            if url and url.startswith('https://res.cloudinary.com/'):
                return url
            
            # Si es ruta local (/media/), devolver null en lugar de la ruta rota
            if url and url.startswith('/media/'):
                return None
                
            # Para cualquier otra URL válida con http/https
            if url and url.startswith('http'):
                return url
                
            return None
            
        except Exception:
            return None