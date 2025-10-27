from django.urls import path
from .views import CreateDeliveryView, BuyerConfirmDeliveryView, PartnerCallbackView

urlpatterns = [
    path("create/", CreateDeliveryView.as_view(), name="create-delivery"),
    path("confirm/", BuyerConfirmDeliveryView.as_view(), name="buyer-confirm"),
    path("callback/", PartnerCallbackView.as_view(), name="partner-callback"),
]
