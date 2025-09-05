from django.db import models
from django.conf import settings
from store.models import Order
from django.utils import timezone

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte bancaire'),
        ('cash', 'Espèces'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('refunded', 'Remboursé'),
    ]

    OPERATORS = [
        ('orange', 'Orange Money'),
        ('moov', 'Moov Money'),
        ('mtn', 'MTN Money'),
        ('card', 'Carte bancaire'),
        ('cash', 'Espèces'),
    ]
    
    PROCESSORS = [
        ('cinetpay', 'CinetPay'),
        ('stripe', 'Stripe'),
        ('manual', 'Manuel'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    operator = models.CharField(max_length=20, choices=OPERATORS)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    phone_number = models.CharField(max_length=20, blank=True)
    processor = models.CharField(max_length=20, choices=PROCESSORS, default='manual')
    processor_token = models.CharField(max_length=255, blank=True)
    processor_response = models.JSONField(null=True, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def update_status(self, new_status, response_data=None):
        """Met à jour le statut du paiement et de la commande associée."""
        if new_status not in dict(self.PAYMENT_STATUS):
            raise ValueError(f"Statut invalide: {new_status}")
        
        self.status = new_status
        if response_data:
            self.processor_response = response_data
            
        if new_status == 'completed':
            self.completed_at = timezone.now()
            self.order.mark_as_paid()
        elif new_status == 'failed':
            self.error_message = response_data.get('error', 'Paiement échoué')
            self.order.status = 'pending'  # Remet la commande en attente
        elif new_status == 'processing':
            self.order.status = 'processing'
        elif new_status == 'refunded':
            self.order.status = 'refunded'
            
        self.order.save()
        self.save()
    
    def complete_payment(self):
        """Marque le paiement comme complété."""
        self.update_status('completed')
    processor_transaction_id = models.CharField(max_length=255, blank=True)
    processor_response = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"Paiement #{self.pk} - {self.get_payment_method_display()} - {self.status}"

    def complete_payment(self):
        """Marque le paiement comme complété et met à jour la commande."""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Met à jour la commande
        self.order.mark_as_paid()
    
    def get_payment_url(self):
        """Retourne l'URL de paiement en fonction du processeur."""
        if self.processor == 'cinetpay':
            return f"https://checkout.cinetpay.com/{self.processor_token}"
        return None
        
    def record_error(self, message):
        """Enregistre une erreur de paiement."""
        self.status = 'failed'
        self.error_message = message
        self.save()
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            # Mise à jour du statut de la commande
            self.order.status = 'paid'
            self.order.paid_at = self.completed_at
            self.order.save()

class PaymentRefund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    refund_transaction_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Payment.PAYMENT_STATUS, default='pending')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"

    def __str__(self):
        return f"Remboursement #{self.pk} pour paiement #{self.payment.pk}"

    def process_refund(self):
        """Traite le remboursement et met à jour le statut du paiement."""
        if self.status != 'completed':
            self.status = 'completed'
            self.processed_at = timezone.now()
            self.save()
            
            # Mise à jour du statut du paiement
            self.payment.status = 'refunded'
            self.payment.save()
