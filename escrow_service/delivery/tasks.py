from celery import shared_task
from django.utils import timezone
from .models import Delivery
from payments.tasks import release_funds
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def wait_for_confirmations(self, delivery_id):
    """
    Waits until buyer confirms delivery before releasing escrow funds.
    Triggered when a delivery is marked as DELIVERED by the partner.
    Retries every X minutes until buyer confirmation is received or max retries reached.
    """
    try:
        delivery = Delivery.objects.get(id=delivery_id)
        escrow_txn = delivery.escrow_transaction

        # If delivery isn't delivered yet, just skip
        if delivery.status != "DELIVERED":
            logger.info(f"Delivery {delivery.id} not yet delivered. Current status: {delivery.status}")
            return

        # Check if buyer confirmed
        if delivery.buyer_confirmed:
            if escrow_txn.payment_status == "HELD":
                logger.info(f"Buyer confirmed for Delivery {delivery.id}. Releasing escrow {escrow_txn.id}")
                release_funds.apply_async(args=[escrow_txn.id])
                delivery.status = "CONFIRMED"
                delivery.updated_at = timezone.now()
                delivery.save()
            else:
                logger.warning(f"Escrow {escrow_txn.id} not in HELD status. Current: {escrow_txn.payment_status}")
        else:
            # Buyer hasn't confirmed yet — retry after delay
            logger.info(f"Waiting for buyer confirmation for Delivery {delivery.id}")
            self.retry(countdown=3600)  # retry after 1 hour

    except Delivery.DoesNotExist:
        logger.error(f"Delivery {delivery_id} not found.")
    except Exception as e:
        logger.exception(f"Error processing delivery {delivery_id}: {str(e)}")
        raise self.retry(exc=e, countdown=600)  # retry after 10 min if failure
