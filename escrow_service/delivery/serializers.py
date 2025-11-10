import uuid
from rest_framework import serializers
from .models import Delivery
from payments.models import EscrowTransaction


class DeliveryCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Delivery
        fields = [
            "order_id",
            "mode",
            "pickup_address",
            "drop_address",
            "partner_name",
        ]

    def validate(self, attrs):
        try:
            escrow_transaction = EscrowTransaction.objects.get(id=attrs["order_id"])
        except EscrowTransaction.DoesNotExist:
            raise serializers.ValidationError("Invalid order_id — no such order found.")
        
        if escrow_transaction.__getattribute__("status") == 'PENDING':
            raise serializers.ValidationError("Error: Pending payment from buyer.")


        mode = attrs.get("mode")

        if mode == "MANUAL":
            # If user provides any of these — reject
            if attrs.get("partner_name"):
                raise serializers.ValidationError("partner_name should not be provided for MANUAL mode.")
            if attrs.get("pickup_address"):
                raise serializers.ValidationError("pickup_address should not be provided for MANUAL mode.")
            if attrs.get("drop_address"):
                raise serializers.ValidationError("drop_address should not be provided for MANUAL mode.")

        elif mode == "PARTNER":
            # These are required for PARTNER mode
            missing_fields = []
            if not attrs.get("partner_name"):
                missing_fields.append("partner_name")
            if not attrs.get("pickup_address"):
                missing_fields.append("pickup_address")
            if not attrs.get("drop_address"):
                missing_fields.append("drop_address")
            if missing_fields:
                raise serializers.ValidationError(
                    f"Missing required fields for PARTNER mode: {', '.join(missing_fields)}"
                )

        else:
            raise serializers.ValidationError("Invalid mode. Must be either MANUAL or PARTNER.")

        return attrs

    def create(self, validated_data):
        escrow_transaction = EscrowTransaction.objects.get(id=validated_data["order_id"])
        tracking_id = f"TRK-{uuid.uuid4().hex[:8].upper()}"

        delivery = Delivery.objects.create(
            escrow_transaction=escrow_transaction,
            mode=validated_data["mode"],
            partner_name=validated_data.get("partner_name"),
            tracking_id=tracking_id,
            pickup_address=validated_data.get("pickup_address", ""),
            drop_address=validated_data.get("drop_address", ""),
        )
        return delivery


class BuyerConfirmSerializer(serializers.Serializer):
    tracking_id = serializers.CharField()
    confirmed = serializers.BooleanField()


class PartnerCallbackSerializer(serializers.Serializer):
    tracking_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["IN_TRANSIT", "DELIVERED", "CANCELLED"])
