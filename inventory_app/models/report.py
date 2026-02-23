# models/report.py
from django.db import models
from .user import User
from inventory_app.managers.soft_delete_manager import SoftDeleteManager


class Report(models.Model):
    file = models.FileField(upload_to='reports/')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Report by {self.user.name} on {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
