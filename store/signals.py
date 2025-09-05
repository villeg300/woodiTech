from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import OrderItem

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    order = instance.order
    order.total_amount = order.total_amount_calculated
    order.save()
