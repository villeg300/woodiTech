from decimal import Decimal
from typing import Dict, Any
import requests
from django.conf import settings
from .base import PaymentProcessor

class CinetPayProcessor(PaymentProcessor):
    """Processeur de paiement pour CinetPay."""
    
    BASE_URL = "https://api-checkout.cinetpay.com/v2"
    
    def __init__(self):
        self.api_key = settings.CINETPAY_API_KEY
        self.site_id = settings.CINETPAY_SITE_ID
        self.notify_url = settings.CINETPAY_NOTIFY_URL
        self.return_url = settings.CINETPAY_RETURN_URL
        self.cancel_url = settings.CINETPAY_CANCEL_URL

    def initialize_payment(self, amount: Decimal, order_id: str, **kwargs) -> Dict[str, Any]:
        try:
            phone_number = kwargs.get('phone_number', '')
            
            payload = {
                'apikey': self.api_key,
                'site_id': self.site_id,
                'transaction_id': str(order_id),
                'amount': int(amount),
                'currency': 'XOF',
                'description': f'Paiement commande #{order_id}',
                'notify_url': self.notify_url,
                'return_url': self.return_url,
                'cancel_url': self.cancel_url,
                'channels': 'ALL',
                'lang': 'fr',
            }
            
            if phone_number:
                payload['customer_phone_number'] = phone_number
            if kwargs.get('customer_name'):
                payload['customer_name'] = kwargs['customer_name']
            if kwargs.get('customer_email'):
                payload['customer_email'] = kwargs['customer_email']

            response = requests.post(f"{self.BASE_URL}/payment", json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get('code') == '201':
                return {
                    'success': True,
                    'payment_url': result['data']['payment_url'],
                    'payment_token': result['data']['payment_token']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Erreur inconnue')
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Erreur de communication avec CinetPay: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        try:
            payload = {
                'apikey': self.api_key,
                'site_id': self.site_id,
                'transaction_id': transaction_id
            }

            response = requests.post(f"{self.BASE_URL}/payment/check", json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get('code') == '00':
                data = result['data']
                return {
                    'success': True,
                    'status': 'completed' if data['status'] == 'ACCEPTED' else 'failed',
                    'amount': Decimal(data['amount']),
                    'currency': data['currency'],
                    'payment_method': data.get('payment_method', ''),
                    'operator_id': data.get('operator_id', ''),
                    'payment_date': data.get('payment_date', '')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Vérification échouée')
                }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Erreur de communication avec CinetPay: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }

    def process_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        try:
            # Vérification de sécurité basique (à améliorer selon les besoins)
            if 'token' not in payload or payload['token'] != self.api_key:
                return {
                    'success': False,
                    'error': 'Token invalide'
                }

            # Traitement des différents états de paiement
            status = payload.get('status')
            if status == 'ACCEPTED':
                return {
                    'success': True,
                    'status': 'completed',
                    'transaction_id': payload.get('transaction_id'),
                    'amount': Decimal(payload.get('amount', '0')),
                    'currency': payload.get('currency'),
                    'payment_method': payload.get('payment_method'),
                    'operator_id': payload.get('operator_id')
                }
            elif status == 'REFUSED':
                return {
                    'success': False,
                    'status': 'failed',
                    'transaction_id': payload.get('transaction_id'),
                    'error': 'Paiement refusé'
                }
            else:
                return {
                    'success': True,
                    'status': 'pending',
                    'transaction_id': payload.get('transaction_id')
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Erreur de traitement du webhook: {str(e)}'
            }
