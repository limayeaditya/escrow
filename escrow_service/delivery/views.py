import requests
from .tasks import wait_for_confirmations
from payments.tasks import release_funds
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Delivery
from payments.models import EscrowTransaction
from .serializers import (
    DeliveryCreateSerializer,
    BuyerConfirmSerializer,
    PartnerCallbackSerializer,
)


# 1️⃣ Seller creates a delivery (manual or partner)
class CreateDeliveryView(APIView):
    def post(self, request):
        serializer = DeliveryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        delivery = serializer.save()

        # If PARTNER → simulate API call to delivery provider
        if delivery.mode == "PARTNER" and delivery.partner_name:
            # Dummy API call (in real case use actual partner endpoint)
            partner_api_url = "https://dummy-partner.com/create-delivery"
            payload = {
                "order_id": delivery.escrow_transaction.id,
                "pickup_address": delivery.pickup_address,
                "drop_address": delivery.drop_address,
                "callback_url": "https://your-escrow-service.com/api/delivery/callback/",
            }
            try:
                # simulate request
                print(f"Simulating API call to {delivery.partner_name}: {payload}")
                # requests.post(partner_api_url, json=payload)
            except Exception as e:
                print(f"Partner API call failed: {e}")

        return Response(
            {
                "message": "Your request has been placed successfully.",
                "delivery_id": delivery.id,
                "mode": delivery.mode,
                "status": delivery.status,
            },
            status=status.HTTP_201_CREATED,
        )


# 2️⃣ Partner webhook / callback endpoint
class PartnerCallbackView(APIView):
    def post(self, request):
        serializer = PartnerCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        tracking_id = serializer.validated_data["tracking_id"]
        status_update = serializer.validated_data["status"]

        delivery = get_object_or_404(Delivery, tracking_id=tracking_id)
        delivery.status = status_update
        delivery.save()

        # If marked as delivered and buyer already confirmed → release funds
        if status_update == "DELIVERED":
            wait_for_confirmations.apply_async(args=[delivery.id])


        return Response({"message": f"Delivery status updated to {status_update}."})


# 3️⃣ Buyer confirmation (works for both MANUAL and PARTNER)
class BuyerConfirmDeliveryView(APIView):
    def post(self, request):
        serializer = BuyerConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        delivery_id = serializer.validated_data["delivery_id"]
        confirmed = serializer.validated_data["confirmed"]

        delivery = get_object_or_404(Delivery, id=delivery_id)
        delivery.buyer_confirmed = confirmed
        delivery.save()

        # Logic to release escrow:
        # - MANUAL → release immediately if buyer confirms
        # - PARTNER → release only if both partner delivered and buyer confirmed
        escrow_transaction = delivery.escrow_transaction
        if confirmed:
            if delivery.mode == "MANUAL" or (delivery.mode == "PARTNER" and delivery.status == "DELIVERED"):
                if escrow_transaction.status == "HELD":
                    delivery.status = "DELIVERED"
                    delivery.save()
                    release_funds.apply_async(args=[escrow_transaction.id], countdown=100)

        return Response({"message": f"Buyer confirmation recorded ({confirmed})."})
