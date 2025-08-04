# models/movement.py
from django.db import models
from .product import Product
from .user import User
from .customer import Customer

class Movement(models.Model):
    movement_type = models.CharField(max_length=50)
    date = models.DateTimeField()
    quantity = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movements')
    stock_in_movement = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.movement_type} - {self.quantity} of {self.product.name}"
