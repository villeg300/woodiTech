from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Category, Product, ProductImage, Cart, CartItem,
    Order, OrderItem, ShippingAddress, PromoCode
)

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Nombre de produits'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'description', 'discount_display',
        'min_amount', 'usage_count', 'valid_period',
        'is_active', 'status_badge'
    )
    list_filter = ('is_active', 'valid_from', 'valid_until')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used',)
    
    def discount_display(self, obj):
        if obj.discount_percentage > 0:
            return f"{obj.discount_percentage}%"
        return f"{obj.discount_amount} FCFA"
    discount_display.short_description = "Remise"
    
    def usage_count(self, obj):
        if obj.usage_limit > 0:
            return f"{obj.times_used}/{obj.usage_limit}"
        return f"{obj.times_used}/∞"
    usage_count.short_description = "Utilisations"
    
    def valid_period(self, obj):
        return format_html(
            "Du {} au {}", 
            obj.valid_from.strftime("%d/%m/%Y"),
            obj.valid_until.strftime("%d/%m/%Y")
        )
    valid_period.short_description = "Période de validité"
    
    def status_badge(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return format_html(
                '<span style="color: red;">Désactivé</span>'
            )
        if now < obj.valid_from:
            return format_html(
                '<span style="color: orange;">En attente</span>'
            )
        if now > obj.valid_until:
            return format_html(
                '<span style="color: red;">Expiré</span>'
            )
        if obj.usage_limit > 0 and obj.times_used >= obj.usage_limit:
            return format_html(
                '<span style="color: red;">Épuisé</span>'
            )
        return format_html(
                '<span style="color: green;">Actif</span>'
            )
    status_badge.short_description = "Statut"

admin.site.register(ProductImage)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    max_num = 4
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'shipping_fee_unit', 'shipping_fee_bulk', 'stock', 'is_available', 'image_preview', 'created_at')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'update_at', 'image_preview')
    inlines = [ProductImageInline]
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Aperçu'
    
    fieldsets = (
        ('Informations produit', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Prix, stock et livraison', {
            'fields': ('price', 'shipping_fee_unit', 'shipping_fee_bulk', 'stock', 'is_available')
        }),
        ('Images', {
            'fields': ('image', 'image_preview')
        }),
        ('Dates', {
            'fields': ('created_at', 'update_at')
        })
    )
    
    
class CartItemInline(admin.TabularInline):

    model = CartItem
    extra = 1
    

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    '''Admin View for Cart'''
    list_display = ('id', 'user', 'created_at', 'total_items')
    inlines = [CartItemInline]
    search_fields = ('user__first_name', 'user__last_name', 'user__phone', 'user__email')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Nb articles'

class OrderItemInline(admin.TabularInline):
    '''Tabular Inline View for OrderItem'''
    model = OrderItem
    extra = 1
    readonly_fields = ('price', 'subtotal')
    fields = ('product', 'quantity', 'price', 'subtotal')
    show_change_link = True

    def subtotal(self, obj):
        return obj.subtotal()
    subtotal.short_description = 'Sous-total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    '''Admin View for Order'''
    list_display = ('id', 'user_info', 'total_amount', 'shipping_fee', 'discount_amount', 'payment_status', 'status', 'created_at', 'shipping_address_info')
    list_select_related = ('user', 'shipping_address')
    inlines = [OrderItemInline]
    search_fields = ('user__first_name', 'user__last_name', 'user__phone', 'user__email', 'id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('total_amount', 'created_at', 'paid_at', 'payment_status', 'payment_details', 'order_items_list')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations commande', {
            'fields': ('user', 'status', 'total_amount', 'order_items_list')
        }),
        ('Livraison', {
            'fields': ('shipping_address',)
        }),
        ('Paiement', {
            'fields': ('payment_status', 'payment_details', 'paid_at')
        }),
        ('Dates', {
            'fields': ('created_at',)
        })
    )

    def user_info(self, obj):
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            full_name = obj.user.get_full_name()
            display_name = full_name if full_name else obj.user.email or obj.user.phone
            return format_html('<a href="{}">{} ({})</a>',
                             url,
                             display_name,
                             obj.user.phone)
        return '-'
    user_info.short_description = 'Client'
    
    def shipping_address_info(self, obj):
        if obj.shipping_address:
            return format_html('{})<br>{}',
                             obj.shipping_address.full_name,
                             obj.shipping_address.phone)
        return '-'
    shipping_address_info.short_description = 'Adresse de livraison'
    
    def order_items_list(self, obj):
        items = obj.items.all()
        if not items:
            return '-'
        items_html = ['<ul>']
        for item in items:
            items_html.append(
                f'<li>{item.quantity}x {item.product.name} - {item.subtotal()} FCFA</li>'
            )
        items_html.append('</ul>')
        return format_html(''.join(items_html))
    order_items_list.short_description = 'Articles'

    def payment_status(self, obj):
        payment = obj.get_latest_payment()
        if not payment:
            return format_html('<span style="color: red;">Non payé</span>')
        
        status_colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        
        color = status_colors.get(payment.status, 'gray')
        status_text = dict(payment.PAYMENT_STATUS).get(payment.status, payment.status)
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            status_text
        )
    payment_status.short_description = 'Statut paiement'

    def payment_details(self, obj):
        payment = obj.get_latest_payment()
        if payment:
            return format_html(
                """
                <strong>Transaction ID:</strong> {}<br>
                <strong>Méthode:</strong> {}<br>
                <strong>Montant:</strong> {} FCFA<br>
                <strong>Date:</strong> {}<br>
                """,
                payment.transaction_id,
                payment.get_payment_method_display(),
                payment.amount,
                payment.created_at.strftime('%d/%m/%Y %H:%M')
            )
        return 'Aucun paiement'
    payment_details.short_description = 'Détails du paiement'

    def total_amount_calculated(self, obj):
        return obj.total_amount_calculated
    total_amount_calculated.short_description = 'Total (calculé)'

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    '''Admin View for ShippingAddress'''
    list_display = ('full_name', 'user_info', 'phone', 'location_info', 'is_default')
    list_filter = ('region', 'city', 'is_default')
    search_fields = ('full_name', 'phone', 'user__email', 'user__phone', 'region', 'city', 'zone')
    ordering = ('-created_at',)
    
    def user_info(self, obj):
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.phone)
        return '-'
    user_info.short_description = 'Client'
    
    def location_info(self, obj):
        return format_html('{} / {} / {}', obj.region, obj.city, obj.zone or '-')
    location_info.short_description = 'Localisation'
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'full_name', 'phone')
        }),
        ('Localisation', {
            'fields': ('region', 'city', 'zone', 'latitude', 'longitude')
        }),
        ('Options', {
            'fields': ('is_default',)
        }),
    )