from django.db import models
from django.utils import timezone
from decimal import Decimal

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=0)  # 0 = unlimited
    times_used = models.PositiveIntegerField(default=0)
    
    def is_valid(self, order_amount):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return False
        if order_amount < self.min_amount:
            return False
        return True
    
    def calculate_discount(self, order_amount):
        if not self.is_valid(order_amount):
            return Decimal('0')
        if self.discount_percentage > 0:
            return (order_amount * self.discount_percentage / 100).quantize(Decimal('0.01'))
        return self.discount_amount
    
    def use(self):
        self.times_used += 1
        self.save()
    
    def __str__(self):
        return self.code

# Modifications à apporter au modèle Order :
"""
class Order(models.Model):
    # ... (champs existants)
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    @property
    def total_amount_calculated(self):
        subtotal = sum(item.price * item.quantity for item in self.items.all())
        if self.promo_code:
            self.discount_amount = self.promo_code.calculate_discount(subtotal)
        return subtotal + self.shipping_fee - self.discount_amount
"""
