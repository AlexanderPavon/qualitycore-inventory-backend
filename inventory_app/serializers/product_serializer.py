# serializers/product_serializer.py
import logging
from rest_framework import serializers
from inventory_app.models.product import Product

logger = logging.getLogger(__name__)

class ProductSerializer(serializers.ModelSerializer):
   image_url = serializers.SerializerMethodField()
   is_active = serializers.SerializerMethodField()
   category_name = serializers.CharField(source='category.name', read_only=True)
   supplier_name = serializers.CharField(source='supplier.name', read_only=True)

   class Meta:
       model = Product
       fields = [
           'id', 'name', 'description', 'category', 'supplier',
           'price', 'minimum_stock', 'current_stock', 'status',
           'image', 'image_url', 'is_active', 'category_name', 'supplier_name',
       ]
       extra_kwargs = {
           "image": {"write_only": True, "required": False},
           'name': {
               'error_messages': {
                   'required': 'El nombre es requerido.',
                   'blank': 'El nombre no puede estar vacío.',
                   'max_length': 'El nombre no puede tener más de 100 caracteres.'
               }
           },
           'price': {
               'error_messages': {
                   'required': 'El precio es requerido.',
                   'invalid': 'Ingrese un precio válido.',
                   'max_digits': 'El precio no puede tener más de 10 dígitos en total.',
                   'max_decimal_places': 'El precio no puede tener más de 2 decimales.'
               }
           },
           'minimum_stock': {
               'error_messages': {
                   'required': 'El stock mínimo es requerido.',
                   'invalid': 'Ingrese un número válido.',
                   'min_value': 'El stock mínimo no puede ser negativo.'
               }
           },
           'current_stock': {
               'error_messages': {
                   'invalid': 'Ingrese un número válido.',
                   'min_value': 'El stock actual no puede ser negativo.'
               }
           },
           'status': {
               'error_messages': {
                   'required': 'El estado es requerido.',
                   'blank': 'El estado no puede estar vacío.',
                   'max_length': 'El estado no puede tener más de 50 caracteres.'
               }
           },
           'category': {
               'error_messages': {
                   'required': 'La categoría es requerida.',
                   'does_not_exist': 'La categoría seleccionada no existe.',
                   'incorrect_type': 'Tipo de dato incorrecto para categoría.'
               }
           },
           'supplier': {
               'error_messages': {
                   'required': 'El proveedor es requerido.',
                   'does_not_exist': 'El proveedor seleccionado no existe.',
                   'incorrect_type': 'Tipo de dato incorrecto para proveedor.'
               }
           }
       }

   def get_is_active(self, obj):
       """
       Convierte el campo status (string) a is_active (booleano).
       Cualquier status que no sea 'Agotado' o 'Inactivo' se considera activo.
       """
       if not obj.status:
           return False
       status_lower = obj.status.lower()
       return status_lower not in ['agotado', 'inactivo', 'out_of_stock', 'inactive']

   def get_image_url(self, obj):
       if not obj.image:
           return None

       try:
           url = obj.image.url
           logger.debug(f"Product {obj.name}: Image URL = {url}")

           # Solo devolver URLs de Cloudinary válidas
           if url and url.startswith('https://res.cloudinary.com/'):
               logger.debug(f"Cloudinary URL found: {url}")
               return url

           # Si es ruta local (/media/), devolver null en lugar de la ruta rota
           if url and url.startswith('/media/'):
               logger.debug(f"Local path detected (Cloudinary not configured): {url}")
               return None

           # Para cualquier otra URL válida con http/https
           if url and url.startswith('http'):
               return url

           return None

       except Exception as e:
           logger.error(f"Error getting image for {obj.name}: {e}")
           return None