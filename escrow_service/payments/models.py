from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User  # Built-in User model

class EscrowTransaction(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending Payment"),
        ("HELD", "Held in Escrow"),
        ("RELEASED", "Released to Seller"),
        ("CANCELLED", "Cancelled"),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_transactions")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.id} | {self.buyer} → {self.seller} | {self.status}"
