# models/quotation.py
from django.db import models
from .customer import Customer
from .user import User

class Quotation(models.Model):
    date = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotations')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quotations')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Quotation {self.id}"
