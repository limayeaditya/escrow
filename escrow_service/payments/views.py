import logging
import json
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import razorpay
from razorpay.errors import SignatureVerificationError
from .serializers import EscrowTransactionSerializer
from .models import EscrowTransaction
from .tasks import release_funds
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import hmac
import hashlib
import json
logger = logging.getLogger(__name__)

class EscrowTransactionList(APIView):
    # permission_classes = [IsAuthenticated]  # optional

    def get(self, request):
        transactions = EscrowTransaction.objects.all().order_by("-id")  # latest first
        serializer = EscrowTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
                    status="PENDING"
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

        body_bytes = request.body
        body_str = body_bytes.decode('utf-8')  # <-- decode bytes to string

        # Verify signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                body_str,
                received_signature,
                webhook_secret
            )
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Invalid signature"}, status=400)

        data = json.loads(body_str)

        if data.get("event") == "payment.captured":
            payment_entity = data["payload"]["payment"]["entity"]
            razorpay_order_id = payment_entity["order_id"]
            payment_id = payment_entity["id"]

            try:
                txn = EscrowTransaction.objects.get(razorpay_order_id=razorpay_order_id)
                txn.razorpay_payment_id = payment_id
                txn.status = "HELD"
                txn.save()

            except EscrowTransaction.DoesNotExist:
                return Response({"error": "Transaction not found"}, status=404)

        return Response({"status": "success"}, status=200)

class RazorpayDemoView(View):
    """
    Serves the Razorpay Checkout demo page.
    """
    template_name = "payments/razorpay_demo.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

