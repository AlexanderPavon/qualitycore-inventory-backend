# models/quoted_product.py
from django.db import models
from .product import Product
from .quotation import Quotation

class QuotedProduct(models.Model):
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='quoted_products')
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='quoted_products')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in quotation {self.quotation.id}"
