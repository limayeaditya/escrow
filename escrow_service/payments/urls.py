from django.urls import path
from .views import CreateRazorpayOrder, RazorpayWebhook

urlpatterns = [
    path("create-order/", CreateRazorpayOrder.as_view(), name="create_order"),
    path("webhook/", RazorpayWebhook.as_view(), name="razorpay_webhook"),

]
