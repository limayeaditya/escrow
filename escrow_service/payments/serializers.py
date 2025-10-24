from rest_framework import serializers
from django.contrib.auth.models import User
from .models import EscrowTransaction

class EscrowTransactionSerializer(serializers.ModelSerializer):
    buyer_id = serializers.IntegerField(write_only=True)
    seller_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = EscrowTransaction
        fields = ["id", "buyer_id", "seller_id", "amount", "status", "razorpay_order_id"]
        read_only_fields = ["id", "status", "razorpay_order_id"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_buyer_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Buyer does not exist.")
        return value

    def validate_seller_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Seller does not exist.")
        return value
    
    def validate(self, attrs):
        """
        Ensure buyer and seller are not the same.
        """
        buyer_id = attrs.get("buyer_id")
        seller_id = attrs.get("seller_id")

        if buyer_id == seller_id:
            raise serializers.ValidationError("Buyer and seller cannot be the same user.")

        return attrs
