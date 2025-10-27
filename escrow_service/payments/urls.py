from django.urls import path
from .views import CreateRazorpayOrder, RazorpayDemoView, RazorpayWebhook, EscrowTransactionList

urlpatterns = [
    path("create-order/", CreateRazorpayOrder.as_view(), name="create_order"),
    path("webhook/", RazorpayWebhook.as_view(), name="razorpay_webhook"),
    path('transactions/', EscrowTransactionList.as_view(), name='transactions_list'),
    path("razorpay-demo/", RazorpayDemoView.as_view(), name="razorpay_demo"),
]
