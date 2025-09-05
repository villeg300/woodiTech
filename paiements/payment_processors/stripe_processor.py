import json
from decimal import Decimal
from typing import Dict, Any
import stripe
from django.conf import settings
from .base import PaymentProcessor
from django.core.exceptions import ValidationError

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeProcessor(PaymentProcessor):
    """Processeur de paiement pour Stripe."""

    def initialize_payment(self, amount: Decimal, order_id: str, **kwargs) -> Dict[str, Any]:
        try:
            # Convertir en centimes pour Stripe
            amount_cents = int(amount * 100)
            
            # Créer l'intention de paiement
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='xof',  # Franc CFA
                metadata={
                    'order_id': order_id
                },
                payment_method_types=['card'],
            )
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(transaction_id)
            return {
                'success': True,
                'status': payment_intent.status,
                'amount': Decimal(payment_intent.amount) / 100,
                'currency': payment_intent.currency,
                'metadata': payment_intent.metadata
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        try:
            # Vérifier la signature du webhook
            sig_header = headers.get('Stripe-Signature')
            if not sig_header:
                raise ValidationError('Signature manquante')

            try:
                event = stripe.Webhook.construct_event(
                    payload=json.dumps(payload),
                    sig_header=sig_header,
                    secret=settings.STRIPE_WEBHOOK_SECRET
                )
            except ValueError as e:
                raise ValidationError('Payload invalide')
            except stripe.error.SignatureVerificationError as e:
                raise ValidationError('Signature invalide')

            # Traiter les différents types d'événements
            if event.type == 'payment_intent.succeeded':
                payment_intent = event.data.object
                return {
                    'success': True,
                    'status': 'completed',
                    'transaction_id': payment_intent.id,
                    'metadata': payment_intent.metadata
                }
            elif event.type == 'payment_intent.payment_failed':
                payment_intent = event.data.object
                return {
                    'success': False,
                    'status': 'failed',
                    'transaction_id': payment_intent.id,
                    'error': payment_intent.last_payment_error.message if payment_intent.last_payment_error else 'Échec du paiement'
                }

            return {
                'success': True,
                'status': 'unknown',
                'type': event.type
            }

        except ValidationError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }
