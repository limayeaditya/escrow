from rest_framework import serializers
from .models import Delivery
from payments.models import EscrowTransaction

class DeliveryCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Delivery
        fields = ["order_id", "mode", "pickup_address", "drop_address", "partner_name", "tracking_id"]

    def validate(self, attrs):
        try:
            escrow_transaction = EscrowTransaction.objects.get(id=attrs["order_id"])
        except EscrowTransaction.DoesNotExist:
            raise serializers.ValidationError("Invalid order_id — no such order found.")
        if attrs["mode"] == "PARTNER" and not attrs.get("partner_name"):
            raise serializers.ValidationError("partner_name is required for PARTNER mode.")
        return attrs

    def create(self, validated_data):
        escrow_transaction = EscrowTransaction.objects.get(id=validated_data["order_id"])
        delivery = Delivery.objects.create(
            escrow_transaction=escrow_transaction,
            mode=validated_data["mode"],
            partner_name=validated_data.get("partner_name"),
            tracking_id=validated_data.get("tracking_id"),
            pickup_address=validated_data["pickup_address"],
            drop_address=validated_data["drop_address"],
        )
        return delivery


class BuyerConfirmSerializer(serializers.Serializer):
    delivery_id = serializers.IntegerField()
    confirmed = serializers.BooleanField()


class PartnerCallbackSerializer(serializers.Serializer):
    tracking_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["IN_TRANSIT", "DELIVERED", "CANCELLED"])
