from functools import wraps
from django.conf import settings
from .payment_processors.stripe_processor import StripeProcessor
from .payment_processors.cinetpay_processor import CinetPayProcessor

def get_payment_processor(payment_method):
    """Retourne le processeur de paiement approprié selon la méthode"""
    if payment_method == 'mobile_money':
        return CinetPayProcessor()
    elif payment_method == 'card':
        return StripeProcessor()
    return None
