from celery import shared_task
from .models import EscrowTransaction
import razorpay
from django.conf import settings
import logging

# Initialize logger
logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@shared_task(bind=True)
def release_funds(self, transaction_id):
    logger.info(f"release_funds task started for transaction ID: {transaction_id}")

    try:
        txn = EscrowTransaction.objects.get(id=transaction_id)
        logger.info(f"Transaction found: ID={txn.id}, Status={txn.status}")

        if txn.status != "HELD":
            logger.warning(f"Transaction {transaction_id} is not in HELD status, skipping release.")
            return f"Transaction {transaction_id} is not in HELD status."

        # Perform Razorpay payout here (or simulate in POC)
        # Example (assuming your seller account is added to Razorpay):
        # payout = razorpay_client.payout.create({
        #     "account_number": txn.seller_account_number,
        #     "amount": int(txn.amount * 100),
        #     "currency": "INR",
        #     "mode": "UPI",
        #     "purpose": "payout"
        # })

        # For POC, just mark as released
        txn.status = "RELEASED"
        txn.save()
        logger.info(f"Transaction {transaction_id} released successfully.")

        return f"Transaction {transaction_id} released successfully."

    except EscrowTransaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} does not exist.")
        return f"Transaction {transaction_id} does not exist."
    except Exception as e:
        logger.exception(f"Error releasing transaction {transaction_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
