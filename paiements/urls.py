from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    path('choice/<int:order_id>/', views.payment_choice, name='payment_choice'),
    path('cash-on-delivery/<int:order_id>/', views.cash_on_delivery, name='cash_on_delivery'),
    path('initialize/<int:order_id>/', views.initialize_payment, name='initialize_payment'),
    path('mobile/<int:payment_id>/', views.process_mobile_payment, name='process_mobile_payment'),
    path('card/<int:payment_id>/', views.process_card_payment, name='process_card_payment'),
    path('success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('history/', views.payment_history, name='payment_history'),
    
    # URLs spécifiques à CinetPay
    path('cinetpay/return/<int:payment_id>/', views.cinetpay_return, name='cinetpay_return'),
    path('cinetpay/notify/', views.cinetpay_webhook, name='cinetpay_notify'),
    path('check-status/<int:payment_id>/', views.check_payment_status, name='check_payment_status'),
    
    # URLs pour Stripe
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
