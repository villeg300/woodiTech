
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from store.models import Order
from .models import Payment, PaymentRefund
from .payment_processors.stripe_processor import StripeProcessor
from .payment_processors.cinetpay_processor import CinetPayProcessor
from .utils import get_payment_processor
import json
import uuid
import stripe

# Configuration de Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

def generate_transaction_id():
    """Génère un ID de transaction unique."""
    return str(uuid.uuid4())

@login_required
@require_POST
def cash_on_delivery(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    # Vérifie que l'adresse est bien Ouagadougou
    if order.shipping_address.city.lower() != 'ouagadougou':
        messages.error(request, "Le paiement à la livraison n'est disponible que pour Ouagadougou.")
        return redirect('paiements:payment_choice', order_id=order.pk)
    # Crée le paiement
    payment = Payment.objects.create(
        order=order,
        user=request.user,
        amount=order.total_amount,
        payment_method='cash',
        operator='cash',
        transaction_id=f"COD-{order.pk}",
        status='completed'
    )
    order.mark_as_paid()
    messages.success(request, "Votre commande a été enregistrée et sera payée à la livraison.")
    return redirect('paiements:payment_success', payment_id=payment.pk)


@login_required
def payment_choice(request, order_id):
    """Affiche les options de paiement pour une commande."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    
    # Vérifie si la commande n'est pas déjà payée
    if order.status == 'paid':
        messages.error(request, "Cette commande a déjà été payée.")
        return redirect('store:order_detail', pk=order.pk)

    return render(request, 'paiements/payment_choice.html', {
        'order': order,
        'payment_methods': Payment.PAYMENT_METHODS,
    })

@login_required
def initialize_payment(request, order_id):
    """Initialise un nouveau paiement."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    
    if request.method == 'POST':
        payment_method = "mobile_money"
        operator = request.POST.get('operator')
        phone_number = request.POST.get('phone_number', '')

        # Validation de base
        if not operator:
            messages.error(request, "Veuillez sélectionner un opérateur.")
            return redirect('paiements:payment_choice', order_id=order.pk)

        # Pour le mobile money, le numéro de téléphone est requis
        if payment_method == 'mobile_money' and not phone_number:
            messages.error(request, "Le numéro de téléphone est requis pour le paiement mobile.")
            return redirect('paiements:payment_choice', order_id=order.pk)

        # Crée le paiement
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            amount=order.total_amount,
            payment_method=payment_method,
            operator=operator,
            transaction_id=generate_transaction_id(),
            phone_number=phone_number
        )

        # Redirige vers la page de confirmation appropriée selon la méthode
        if payment_method == 'mobile_money':
            return redirect('paiements:process_mobile_payment', payment_id=payment.pk)
        #elif payment_method == 'card':
            #return redirect('paiements:process_card_payment', payment_id=payment.pk)
        #else:
            #return redirect('paiements:payment_success', payment_id=payment.pk)

    return redirect('paiements:payment_choice', order_id=order.pk)

@login_required
def process_mobile_payment(request, payment_id):
    """Traite un paiement mobile money."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    
    if payment.status != 'pending':
        messages.error(request, "Ce paiement ne peut plus être modifié.")
        return redirect('store:order_detail', payment.order.pk)

    if request.method == 'POST':
        processor = get_payment_processor('mobile_money')
        if not processor:
            messages.error(request, "Mode de paiement non disponible.")
            return redirect('store:order_detail', pk=payment.order.pk)
        
        try:
            # Initialiser le paiement avec CinetPay
            result = processor.initialize_payment(
                amount=payment.amount,
                order_id=payment.transaction_id,
                customer_name=f"{payment.user.first_name} {payment.user.last_name}",
                customer_email=payment.user.email,
                customer_phone_number=payment.phone_number
            )
            
            if result['success']:
                payment.processor = 'cinetpay'
                payment.processor_response = result
                payment.status = 'processing'
                payment.save()
                
                return redirect(result['payment_url'])
            else:
                raise Exception(result.get('error', 'Erreur lors de l\'initialisation du paiement'))
        except Exception as e:
            messages.error(request, f"Erreur lors de l'initialisation du paiement: {str(e)}")
            return redirect('store:order_detail', pk=payment.order.pk)

    return render(request, 'paiements/mobile_payment.html', {'payment': payment})

@login_required
def process_card_payment(request, payment_id):
    """Traite un paiement par carte."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    
    if payment.status != 'pending':
        messages.error(request, "Ce paiement ne peut plus être modifié.")
        return redirect('store:order_detail', payment.order.pk)

    if request.method == 'POST':
        processor = get_payment_processor('card')
        if not processor:
            messages.error(request, "Mode de paiement non disponible.")
            return redirect('store:order_detail', pk=payment.order.pk)
        
        try:
            # En production, initialiser le paiement avec Stripe
            result = processor.initialize_payment(payment)
            payment.processor = 'stripe'
            payment.processor_response = result
            payment.save()
            
            return render(request, 'paiements/stripe_redirect.html', {
                'session_id': result['session_id'],
                'public_key': result['public_key']
            })
        except Exception as e:
            messages.error(request, f"Erreur lors de l'initialisation du paiement: {str(e)}")
            return redirect('store:order_detail', pk=payment.order.pk)

    return render(request, 'paiements/card_payment.html', {'payment': payment})

@login_required
def payment_success(request, payment_id):
    """Affiche la page de confirmation après un paiement réussi."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    return render(request, 'paiements/payment_success.html', {'payment': payment})

@csrf_exempt
def stripe_webhook(request):
    """Webhook pour Stripe."""
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    processor = get_payment_processor('card')
    if not processor:
        return HttpResponse(status=200)

    try:
        payment_id, success = processor.process_webhook(request)
        if success and payment_id:
            payment = Payment.objects.get(id=payment_id)
            payment.complete_payment()
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(str(e), status=400)

@csrf_exempt
@require_POST
def cinetpay_webhook(request):
    """Webhook pour CinetPay."""
    processor = get_payment_processor('mobile_money')
    if not processor:
        return HttpResponse(status=400)

    try:
        payload = json.loads(request.body)
        result = processor.process_webhook(payload, request.headers)
        
        if result['success']:
            payment = Payment.objects.get(transaction_id=result['transaction_id'])
            payment.update_status(result['status'], payload)
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': result.get('error', 'Unknown error')})
            
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    except Payment.DoesNotExist:
        return HttpResponse("Payment not found", status=404)
    except Exception as e:
        return HttpResponse(str(e), status=400)

@login_required
def payment_history(request):
    """Affiche l'historique des paiements de l'utilisateur."""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'paiements/payment_history.html', {'payments': payments})

@login_required
def cinetpay_return(request, payment_id):
    """Page de retour après paiement CinetPay."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    
    # Vérifie le statut du paiement
    processor = get_payment_processor('mobile_money')
    if processor:
        try:
            result = processor.verify_payment(payment.transaction_id)
            if result['success']:
                payment.status = result['status']
                payment.completed_at = timezone.now() if result['status'] == 'completed' else None
                payment.save()
                
                if result['status'] == 'completed':
                    payment.order.mark_as_paid()
        except Exception as e:
            messages.error(request, f"Erreur lors de la vérification du paiement: {str(e)}")
    
    return render(request, 'paiements/cinetpay_return.html', {'payment': payment})

@login_required
def check_payment_status(request, payment_id):
    """Vérifie le statut d'un paiement."""
    payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
    processor = get_payment_processor('mobile_money')
    
    if processor:
        try:
            result = processor.verify_payment(payment.transaction_id)
            if result['success']:
                payment.update_status(result['status'], result)
                return JsonResponse({'status': payment.status})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': payment.status})
