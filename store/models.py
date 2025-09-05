from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from utils.my_uuid import uuid_slug
from django.conf import settings
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

    class Meta:
        verbose_name = "Code Promo"
        verbose_name_plural = "Codes Promo"
    
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
        # Vérifie si le code n'est pas expiré depuis plus de 24h
        if (now - self.valid_until).days > 1:
            self.is_active = False
            self.save()
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


class Category(models.Model):
    name = models.CharField(max_length=75)
    slug = models.SlugField(max_length=75, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories', blank=True, null=True)
    created_at = models.DateTimeField( auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    

class Product (models.Model):
    shipping_fee_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Frais livraison unitaire")
    shipping_fee_bulk = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Frais livraison (gros)")
    name = models.CharField(max_length=125)
    slug = models.SlugField(max_length=75, blank=True)
    category = models.ForeignKey("Category",null=True, on_delete=models.SET_NULL, related_name='products')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock= models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to='products/mains/', blank=False, null=False)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField( auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)   
    
    def save(self, *args, **kwargs):
        if not self.slug:
            uuid = uuid_slug(5)
            self.slug = slugify(f"{self.name}-{self.pk}-{uuid}")
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} [x{self.stock}]"


class ProductImage(models.Model):
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name='more_images')
    image = models.ImageField(upload_to='products/others/')
    alt_text = models.CharField(max_length=250, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.alt_text:
            self.alt_text = f"image {self.product.name}"
        return super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = ("autre image")
        verbose_name_plural = ("autres images")

    def __str__(self):
        return f"image[{self.pk}]:{self.product.slug}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('store:product_detail', kwargs={'pk': self.pk})


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def total(self):
        return sum(item.subtotal() for item in self.items.all())
    
    def get_shipping_fee(self):
        """Calcule les frais de livraison pour tous les articles du panier"""
        shipping_fee = Decimal('0')
        for item in self.items.all():
            if item.quantity >= 5 and item.product.shipping_fee_bulk > 0:
                fee = item.product.shipping_fee_bulk * (item.quantity // 5) + item.product.shipping_fee_unit * (item.quantity % 5)
            else:
                fee = item.product.shipping_fee_unit * item.quantity
            shipping_fee += fee
        return shipping_fee
    
    def get_total_with_shipping(self):
        """Calcule le total avec les frais de livraison"""
        return self.total() + self.get_shipping_fee()
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    class Meta:
        verbose_name = ("Cart")
        verbose_name_plural = ("Carts")

    def __str__(self):
        return f"Cart[{self.pk}]{self.user.first_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('store:cart')


class CartItem(models.Model):

    cart = models.ForeignKey("Cart", on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey("Product",on_delete=models.CASCADE)
    quantity = models.PositiveBigIntegerField(default=1)
    
    def subtotal(self):
        return self.product.price * self.quantity

    class Meta:
        unique_together = ('cart', 'product')
        verbose_name = ("CartItem")
        verbose_name_plural = ("CartItems")

    def __str__(self):
        return self.product.name

    def get_absolute_url(self):
        #return reverse("CartItem_detail", kwargs={"pk": self.pk})
        pass


class ShippingAddress(models.Model):
    def get_shipping_fee(self):
        # Exemple simple : zone ou ville, à adapter selon la logique métier
        if self.city.lower() == 'abidjan':
            return 1000
        elif self.city:
            return 2000
        return 3000
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shipping_addresses')
    full_name = models.CharField(max_length=250)
    phone = models.CharField(max_length=100)
    region = models.CharField(max_length=150)
    city = models.CharField(max_length=150)
    
    zone = models.CharField(max_length=150, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at =models.DateTimeField(auto_now_add=True)
    

    class Meta:
        verbose_name = ("Adresse de livraison")
        verbose_name_plural = ("Adresses de livraisons")
        ordering = ['created_at']
        
    def __str__(self):
        return f'{self.full_name} - {self.city} {self.zone}'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('store:edit_address', kwargs={'pk': self.pk})


class OrderItem(models.Model):
    order = models.ForeignKey("Order",on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey("Product", on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def subtotal(self):
        return self.price * self.quantity
 
    def save(self, *args, **kwargs):
        
        if not self.product:
            price = self.price
            self.price = price
        price = self.product.price
        self.price = price
        super().save(*args, **kwargs)  
    
    def __str__(self):
        return f"{self.product.name}[{self.quantity}]"


class Order(models.Model):
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('store:order_detail', kwargs={'pk': self.pk})
    STATUS = (
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('paid', 'Payée'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    cart = models.ForeignKey("Cart",null=True,blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=50, choices=STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_address = models.ForeignKey("ShippingAddress", null=True, on_delete=models.SET_NULL)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    promo_code = models.ForeignKey("PromoCode", null=True, blank=True, on_delete=models.SET_NULL)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    

    def save(self, *args, **kwargs):
        if not self.pk:  # Si c'est une nouvelle commande
            if self.promo_code and self.promo_code.is_valid(self.total_amount):
                self.discount_amount = self.promo_code.calculate_discount(self.total_amount)
                self.promo_code.use()
            else:
                self.discount_amount = Decimal('0')
                self.promo_code = None
        super().save(*args, **kwargs)

    @property
    def total_amount_calculated(self):
        subtotal = sum(item.price * item.quantity for item in self.items.all())
        if self.promo_code and self.promo_code.is_valid(subtotal):
            self.discount_amount = self.promo_code.calculate_discount(subtotal)
            if self.discount_amount > subtotal:
                self.discount_amount = subtotal
        return subtotal + self.shipping_fee - self.discount_amount
    
    def mark_as_paid(self):
        """Marque la commande comme payée."""
        from django.utils import timezone
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()
        
    def has_pending_payment(self):
        """Vérifie si la commande a un paiement en attente."""
        return self.payments.filter(status='pending').exists()
    
    def get_latest_payment(self):
        """Récupère le dernier paiement de la commande."""
        return self.payments.order_by('-created_at').first()
    
    def __str__(self):
        return f"commande {self.pk} - {self.user} -{self.status}"





