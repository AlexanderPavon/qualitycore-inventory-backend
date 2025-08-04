from django.apps import AppConfig
from django.contrib.auth import get_user_model
import logging

class InventoryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory_app'

    def ready(self):
        from django.db.utils import OperationalError, ProgrammingError
        User = get_user_model()
        try:
            # Primer superusuario
            if not User.objects.filter(email='a.alexanderpavon@gmail.com').exists():
                User.objects.create_superuser(
                    email='a.alexanderpavon@gmail.com',
                    password='Alex123',
                    name='Alexander Pavón',
                    role='Administrator'
                )
                logging.info("✅ Superuser 1 creado: a.alexanderpavon@gmail.com / Alex123")

            # Segundo superusuario
            if not User.objects.filter(email='alisonlizbethch@gmail.com').exists():
                User.objects.create_superuser(
                    email='alisonlizbethch@gmail.com',
                    password='Ali123',
                    name='Alison Carrion',
                    role='Administrator'
                )
                logging.info("✅ Superuser 2 creado: alcarrion@puce.edu.ec / Ali123")

        except (OperationalError, ProgrammingError):
            pass  # Evita errores si la base aún no está lista
