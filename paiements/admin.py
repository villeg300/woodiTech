from django.contrib import admin
from .models import Payment, PaymentRefund
from django.utils.html import format_html


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'order_link', 'amount', 'payment_method', 
                   'operator', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'operator', 'created_at')
    search_fields = ('transaction_id', 'user__email', 'user__phone', 'order__id')
    readonly_fields = ('transaction_id', 'created_at')
    ordering = ('-created_at',)
    
    def order_link(self, obj):
        if obj.order:
            url = f"/admin/store/order/{obj.order.id}/change/"
            return format_html('<a href="{}">{}</a>', url, f"Commande #{obj.order.id}")
        return "-"
    order_link.short_description = "Commande"

    fieldsets = (
        ('Informations de paiement', {
            'fields': ('transaction_id', 'user', 'order', 'amount', 'status')
        }),
        ('Méthode de paiement', {
            'fields': ('payment_method', 'operator', 'phone_number')
        }),
        ('Dates', {
            'fields': ('created_at', 'completed_at')
        }),
    )


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ('payment', 'amount', 'status', 'reason', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__transaction_id', 'reason')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    fieldsets = (
        ('Informations du remboursement', {
            'fields': ('payment', 'amount', 'status', 'reason')
        }),
        ('Dates', {
            'fields': ('created_at', 'processed_at')
        }),
    )
