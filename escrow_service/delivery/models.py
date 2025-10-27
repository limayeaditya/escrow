from django.db import models
from payments.models import EscrowTransaction


class Delivery(models.Model):
    MODE_CHOICES = [
        ("MANUAL", "Manual by Seller"),
        ("PARTNER", "Third Party Partner"),
    ]

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    escrow_transaction = models.OneToOneField(EscrowTransaction, on_delete=models.CASCADE, related_name="delivery")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    partner_name = models.CharField(max_length=100, blank=True, null=True)
    tracking_id = models.CharField(max_length=100, blank=True, null=True)
    pickup_address = models.TextField(default="")
    drop_address = models.TextField(default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    buyer_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.id} ({self.mode})"
