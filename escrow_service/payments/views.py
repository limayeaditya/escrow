from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import razorpay
from .serializers import EscrowTransactionSerializer
from .models import EscrowTransaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import hmac
import hashlib
import json

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class CreateRazorpayOrder(APIView):
    def post(self, request):
        serializer = EscrowTransactionSerializer(data=request.data)
        if serializer.is_valid():
            buyer = serializer.validated_data["buyer_id"]
            seller = serializer.validated_data["seller_id"]
            amount = serializer.validated_data["amount"] * 100  # Razorpay expects paise

            try:
                # Create Razorpay order
                order = razorpay_client.order.create({
                    "amount": int(amount),
                    "currency": "INR",
                    "payment_capture": 1
                })

                # Save transaction in DB
                transaction = EscrowTransaction.objects.create(
                    buyer_id=buyer,
                    seller_id=seller,
                    amount=amount / 100,
                    razorpay_order_id=order["id"],
                    status="HELD"
                )

                return Response({
                    "transaction_id": transaction.id,
                    "razorpay_order_id": order["id"],
                    "status": transaction.status
                }, status=status.HTTP_201_CREATED)

            except razorpay.errors.BadRequestError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({"error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhook(APIView):
    def post(self, request):
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        received_signature = request.headers.get('X-Razorpay-Signature')
        body = request.body

        # Verify webhook signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if received_signature != expected_signature:
            return HttpResponse(status=400)

        data = json.loads(body)

        # Handle payment captured event
        if data.get("event") == "payment.captured":
            payment_entity = data["payload"]["payment"]["entity"]
            razorpay_order_id = payment_entity["order_id"]
            payment_id = payment_entity["id"]

            try:
                txn = EscrowTransaction.objects.get(razorpay_order_id=razorpay_order_id)
                txn.razorpay_payment_id = payment_id
                txn.status = "HELD"  # Payment received and held in escrow
                txn.save()

                # Optional: trigger Celery task to release funds later
                # release_funds.apply_async(args=[txn.id], countdown=86400)  # 24h later

            except EscrowTransaction.DoesNotExist:
                return HttpResponse(status=404)

        return HttpResponse(status=200)
