# inventory_app/signals.py
import logging
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def create_default_superusers(sender, **kwargs):
    # corre solo cuando la migración corresponde a esta app
    app_config = kwargs.get("app_config")
    if app_config and app_config.name != "inventory_app":
        return

    User = get_user_model()
    users = [
        ("a.alexanderpavon@gmail.com", "Alex123", "Alexander Pavón"),
        ("alisonlizbethch@gmail.com", "Ali123", "Alison Carrion"),
    ]
    for email, pwd, name in users:
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email, password=pwd, name=name, role="Administrator"
            )
            logger.info(f"✅ Superuser creado: {email}")
