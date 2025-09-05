from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import Product, Cart, CartItem, Order, OrderItem, ShippingAddress, PromoCode


def home(request):
    
    featured_products = Product.objects.filter(is_available=True).order_by('-created_at')[:6]
    context = {
        'featured_products': featured_products
    }
    return render(request, 'store/home.html',context=context)

@login_required
def livreur_dashboard(request):
    # Affiche les commandes à livrer (exemple: status='pending')
    commandes = Order.objects.filter(status='pending').order_by('-created_at')
    return render(request, 'store/livreur_dash.html', {'commandes': commandes})

# Vue produits par catégorie
def category_products(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = Product.objects.filter(category=category, is_available=True)
    return render(request, 'store/category_products.html', {'category': category, 'products': products})



@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    promo_code = None
    discount = Decimal('0')
    shipping_fee = Decimal('0')
    shipping_details = []
    total = Decimal('0')

    # Calculer les frais de livraison si le panier n'est pas vide
    if cart.items.exists():
        # Calcul des frais de livraison par article
        for item in cart.items.all():
            # Si plus de 5 articles et frais de livraison en gros disponible
            if item.quantity >= 5 and item.product.shipping_fee_bulk > 0:
                # Calcul des frais pour les lots de 5 + frais unitaires pour le reste
                bulk_count = item.quantity // 5  # Nombre de lots de 5
                remaining = item.quantity % 5     # Articles restants
                fee = (item.product.shipping_fee_bulk * bulk_count) + (item.product.shipping_fee_unit * remaining)
                if bulk_count > 0:
                    label = f"{item.product.name}: {bulk_count} lots de 5 à {item.product.shipping_fee_bulk} FCFA/lot"
                    if remaining > 0:
                        label += f" + {remaining} unités à {item.product.shipping_fee_unit} FCFA/unité"
            else:
                # Calcul des frais unitaires standards
                fee = item.product.shipping_fee_unit * item.quantity
                label = f"{item.product.name}: {item.quantity} unités à {item.product.shipping_fee_unit} FCFA/unité"
            
            # Ajouter les frais de livraison s'ils sont supérieurs à 0
            if fee > 0:
                shipping_fee += fee
                shipping_details.append({'label': label, 'fee': fee})

        # Sous-total avant remise
        subtotal = cart.total()
        
        # Vérification et application du code promo
        if 'promo_code' in request.session:
            try:
                code = request.session['promo_code']
                promo_code = PromoCode.objects.get(code=code, is_active=True)
                
                if promo_code.is_valid(subtotal):
                    discount = promo_code.calculate_discount(subtotal)
                else:
                    del request.session['promo_code']
                    promo_code = None
                    messages.warning(request, "Le code promo n'est plus valide pour ce montant.")
            except PromoCode.DoesNotExist:
                del request.session['promo_code']
                messages.error(request, "Code promo inexistant ou expiré.")

        # Calcul du total final
        total = subtotal + shipping_fee - discount

    context = {
        'cart': cart,
        'promo_code': promo_code,
        'discount': discount,
        'shipping_fee': shipping_fee,
        'shipping_details': shipping_details,
        'total': total,
        'subtotal': subtotal if 'subtotal' in locals() else Decimal('0')
    }
    return render(request, 'store/cart.html', context)

from django.core.cache import cache
from django.utils import timezone

@login_required
def apply_promo(request):
    if request.method == 'POST':
        # Vérifie le nombre de tentatives
        cache_key = f'promo_attempts_{request.user.id}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:  # Maximum 5 tentatives par heure
            messages.error(request, "Vous avez fait trop de tentatives. Veuillez réessayer dans une heure.")
            return redirect('store:cart')
            
        code = request.POST.get('code')
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
            cart = Cart.objects.get(user=request.user)
            
            # Vérifie si le code a déjà été utilisé par cet utilisateur
            usage_key = f'promo_usage_{code}_{request.user.id}'
            if cache.get(usage_key):
                messages.error(request, "Vous avez déjà utilisé ce code promo.")
                return redirect('store:cart')
            
            if not promo.is_valid(cart.total()):
                messages.error(request, "Ce code promo n'est pas valide pour votre commande.")
            else:
                request.session['promo_code'] = promo.code
                discount = promo.calculate_discount(cart.total())
                messages.success(request, f"Code promo appliqué ! Vous économisez {discount} FCFA")
                
                # Marque le code comme utilisé par cet utilisateur
                cache.set(usage_key, True, timeout=60*60*24*30)  # 30 jours
                return redirect('store:cart')
                
        except PromoCode.DoesNotExist:
            messages.error(request, "Code promo invalide ou expiré.")
        
        # Incrémente le compteur de tentatives
        cache.set(cache_key, attempts + 1, timeout=60*60)  # 1 heure
    
    return redirect('store:cart')
from django.contrib.auth import get_user_model
from .models import Product, Cart, CartItem, Order, OrderItem, ShippingAddress, PromoCode
from django.urls import reverse
from django.contrib import messages
from django.db import transaction

def contact(request):
    if request.method == 'POST':
        # Ici, tu peux traiter l'envoi du message (email, base, etc.)
        messages.success(request, "Votre message a été envoyé !")
    return render(request, 'store/contact.html')

@login_required
def admin_dashboard(request):
    User = get_user_model()
    nb_clients = User.objects.filter(is_staff=False).count()
    nb_livreurs = User.objects.filter(role='livreur').count()
    nb_commandes = Order.objects.count()
    total_revenus = Order.objects.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    total_shipping_fees = Order.objects.filter(status='paid').aggregate(total=Sum('shipping_fee'))['total'] or 0
    recent_activities = [
        f"Commande #{o.id} créée par {o.user.first_name}" for o in Order.objects.order_by('-created_at')[:5]
    ]
    return render(request, 'store/admin_dash.html', {
        'nb_clients': nb_clients,
        'nb_livreurs': nb_livreurs,
        'nb_commandes': nb_commandes,
        'total_revenus': total_revenus,
        'total_shipping_fees': total_shipping_fees,
        'recent_activities': recent_activities,
    })

@login_required
def admin_product_list(request):
    products = Product.objects.all().order_by('-created_at')
    query = request.GET.get('q')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'store/admin_product_list.html', {'products': products, 'query': query})

@login_required
def admin_add_product(request):
    from .models import Category, ProductImage
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        category_id = request.POST.get('category')
        category = Category.objects.get(pk=category_id) if category_id else None
        shipping_fee_unit = request.POST.get('shipping_fee_unit') or 0
        shipping_fee_bulk = request.POST.get('shipping_fee_bulk') or 0
        is_available = bool(request.POST.get('is_available'))
        product = Product.objects.create(
            name=name,
            price=price,
            description=description,
            image=image,
            category=category,
            shipping_fee_unit=shipping_fee_unit,
            shipping_fee_bulk=shipping_fee_bulk,
            is_available=is_available
        )
        # Gérer les images supplémentaires
        more_images = request.FILES.getlist('more_images')
        for img in more_images:
            ProductImage.objects.create(product=product, image=img)
        messages.success(request, 'Produit ajouté.')
        return redirect('store:admin_product_list')
    return render(request, 'store/admin_product_form.html', {'categories': categories})

@login_required
def admin_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    from .models import Category, ProductImage
    categories = Category.objects.all()
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.price = request.POST.get('price')
        product.description = request.POST.get('description')
        product.shipping_fee_unit = request.POST.get('shipping_fee_unit') or 0
        product.shipping_fee_bulk = request.POST.get('shipping_fee_bulk') or 0
        product.is_available = bool(request.POST.get('is_available'))
        category_id = request.POST.get('category')
        product.category = Category.objects.get(pk=category_id) if category_id else None
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        # Gérer les images supplémentaires
        more_images = request.FILES.getlist('more_images')
        for img in more_images:
            ProductImage.objects.create(product=product, image=img)
        messages.success(request, 'Produit modifié.')
        return redirect('store:admin_product_list')
    return render(request, 'store/admin_product_form.html', {'product': product, 'categories': categories})

@login_required
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Produit supprimé.')
        return redirect('store:admin_product_list')
    return render(request, 'store/admin_product_confirm_delete.html', {'product': product})

@login_required
def admin_livreur_list(request):
    User = get_user_model()
    livreurs = User.objects.filter(role='livreur')
    return render(request, 'store/admin_livreur_list.html', {'livreurs': livreurs})

@login_required
def admin_add_livreur(request):
    User = get_user_model()
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email') or f"{phone}@wooditech.local"
        if not phone:
            messages.error(request, "Le numéro de téléphone est obligatoire.")
            return render(request, 'store/admin_livreur_form.html')
        user = User.objects.create_user(phone=phone, email=email, password=password, role='livreur', is_staff=False, first_name=first_name, last_name=last_name)
        user.save()
        messages.success(request, 'Livreur ajouté.')
        return redirect('store:admin_livreur_list')
    return render(request, 'store/admin_livreur_form.html')

@login_required
def admin_edit_livreur(request, pk):
    User = get_user_model()
    livreur = get_object_or_404(User, pk=pk, role='livreur')
    if request.method == 'POST':
        livreur.username = request.POST.get('username')
        livreur.save()
        messages.success(request, 'Livreur modifié.')
        return redirect('store:admin_livreur_list')
    return render(request, 'store/admin_livreur_form.html', {'livreur': livreur})

@login_required
def admin_delete_livreur(request, pk):
    User = get_user_model()
    livreur = get_object_or_404(User, pk=pk, role='livreur')
    if request.method == 'POST':
        livreur.delete()
        messages.success(request, 'Livreur supprimé.')
        return redirect('store:admin_livreur_list')
    return render(request, 'store/admin_livreur_confirm_delete.html', {'livreur': livreur})
# --- CRUD CATEGORIES ---
from .models import Category

@login_required
def admin_category_list(request):
    categories = Category.objects.all()
    return render(request, 'store/admin_category_list.html', {'categories': categories})

@login_required
def admin_add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = Category.objects.create(name=name, description=description)
        messages.success(request, 'Catégorie ajoutée.')
        return redirect('store:admin_category_list')
    return render(request, 'store/admin_category_form.html')

@login_required
def admin_edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.save()
        messages.success(request, 'Catégorie modifiée.')
        return redirect('store:admin_category_list')
    return render(request, 'store/admin_category_form.html', {'category': category})

@login_required
def admin_delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Catégorie supprimée.')
        return redirect('store:admin_category_list')
    return render(request, 'store/admin_category_confirm_delete.html', {'category': category})

@login_required
def admin_user_list(request):
    User = get_user_model()
    users = User.objects.filter(is_staff=False)
    return render(request, 'store/admin_user_list.html', {'users': users})

@login_required
def admin_order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'store/admin_order_list.html', {'orders': orders})

@login_required
def admin_product_search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'store/admin_product_list.html', {'products': products, 'query': query})




# Tableau de bord client
@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    addresses = ShippingAddress.objects.filter(user=request.user)
    admin_link = None
    livreur_link = None
    if request.user.is_authenticated:
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            admin_link = 'store:admin_dashboard'
        elif hasattr(request.user, 'role') and request.user.role == 'livreur':
            livreur_link = 'store:livreur_dashboard'
    return render(request, 'store/dashboard.html', {
        'orders': orders,
        'addresses': addresses,
        'admin_link': admin_link,
        'livreur_link': livreur_link,
    })


# Liste des produits

def product_list(request):
    products = Product.objects.filter(is_available=True)
    search_query = request.GET.get('q')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
        
    return render(request, 'store/product_list.html', {
        'products': products,
        'search_query': search_query
    })

# Détail produit

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {'product': product}
    item = {'quantity': 0}
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        try:
            item = CartItem.objects.get(cart=cart, product=product)
        except CartItem.DoesNotExist:
            pass
            
    context["item"] = item
        
    return render(request, 'store/product_detail.html', context=context)

# Vue du panier supprimée car déjà définie plus haut dans le fichier

@login_required
def apply_promo(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
            cart = Cart.objects.get(user=request.user)
            
            if not promo.is_valid(cart.total()):
                messages.error(request, "Ce code promo n'est pas valide pour votre commande.")
                return redirect('store:cart')
                
            request.session['promo_code'] = promo.code
            messages.success(request, f"Code promo '{promo.code}' appliqué avec succès!")
            
        except PromoCode.DoesNotExist:
            messages.error(request, "Code promo invalide.")
        
    return redirect('store:cart')

# Ajouter au panier
@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        try:
            qty = int(request.POST.get('quantity', 1))
            item, created = CartItem.objects.get_or_create(cart=cart, product=product)  
            if not created:
                if qty > 0:
                    item.quantity += qty
                    item.save()
                else:
                    item.delete()
                    messages.info(request, "Article supprimé du panier.")
            messages.success(request, f"{product.name} ajouté au panier.")
        except Exception:
            messages.error(request, "Erreur de mise à jour.")
            
    
    return redirect('store:product_detail', pk)

# Modifier quantité
@login_required
def update_cart_item(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    if request.method == 'POST':
        try:
            qty = int(request.POST.get('quantity', 1))
            if qty > 0:
                item.quantity = qty
                item.save()
                messages.success(request, "Quantité mise à jour.")
            else:
                item.delete()
                messages.info(request, "Article supprimé du panier.")
        except Exception:
            messages.error(request, "Erreur de mise à jour.")
    return redirect('store:cart')

# Supprimer du panier
@login_required
def remove_from_cart(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    item.delete()
    messages.info(request, "Article supprimé du panier.")
    return redirect('store:cart')

# Checkout with address selection
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    addresses = ShippingAddress.objects.filter(user=request.user)
    selected_address_id = request.POST.get('address') if request.method == 'POST' else None
    selected_address = None
    
    # Récupération du code promo
    promo_code = None
    if 'promo_code' in request.session:
        try:
            promo_code = PromoCode.objects.get(code=request.session['promo_code'])
            if not promo_code.is_valid(cart.total()):
                promo_code = None
                del request.session['promo_code']
        except PromoCode.DoesNotExist:
            del request.session['promo_code']
    
    if selected_address_id:
        try:
            selected_address = addresses.get(pk=selected_address_id)
        except ShippingAddress.DoesNotExist:
            selected_address = None
            
    if request.method == 'POST':
        if not selected_address:
            messages.error(request, "Veuillez sélectionner une adresse de livraison valide.")
        else:
            with transaction.atomic():
                # Calculer les frais de livraison
                shipping_fee = Decimal('0')
                if cart.items.exists():
                    for item in cart.items.all():
                        if item.quantity >= 5 and item.product.shipping_fee_bulk > 0:
                            bulk_count = item.quantity // 5
                            remaining = item.quantity % 5
                            fee = (item.product.shipping_fee_bulk * bulk_count) + (item.product.shipping_fee_unit * remaining)
                        else:
                            fee = item.product.shipping_fee_unit * item.quantity
                        shipping_fee += fee
                
                # Calculer le sous-total et le total
                subtotal = cart.total()
                total = subtotal + shipping_fee
                
                # Appliquer la réduction si un code promo est valide
                if promo_code and promo_code.is_valid(subtotal):
                    total -= promo_code.calculate_discount(subtotal)

                # Créer la commande
                order = Order.objects.create(
                    user=request.user,
                    shipping_address=selected_address,
                    status='pending',
                    shipping_fee=shipping_fee,
                    total_amount=total,
                    promo_code=promo_code
                )

                # Ajouter les articles de la commande
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                
                # Vider le panier
                cart.items.all().delete()
                
                if promo_code:
                    promo_code.use()
                    del request.session['promo_code']
                # Redirection vers le choix du mode de paiement
                return redirect('paiements:payment_choice', order.pk)
    return render(request, 'store/checkout.html', {
        'cart': cart,
        'addresses': addresses,
        'selected_address': selected_address,
    })

# Gérer les adresses de livraison
@login_required
def manage_addresses(request):
    addresses = ShippingAddress.objects.filter(user=request.user)
    return render(request, 'store/manage_addresses.html', {'addresses': addresses})

# Ajouter une adresse
@login_required
def add_address(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        region = request.POST.get('region')
        city = request.POST.get('city')
        zone = request.POST.get('zone')
        is_default = bool(request.POST.get('is_default'))
        address = ShippingAddress.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            region=region,
            city=city,
            zone=zone,
            is_default=is_default
        )
        if is_default:
            ShippingAddress.objects.filter(user=request.user).exclude(pk=address.pk).update(is_default=False)
        messages.success(request, "Adresse ajoutée.")
        return redirect('store:manage_addresses')
    return render(request, 'store/add_address.html')

# Modifier une adresse
@login_required
def edit_address(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk, user=request.user)
    if request.method == 'POST':
        address.full_name = request.POST.get('full_name')
        address.phone = request.POST.get('phone')
        address.region = request.POST.get('region')
        address.city = request.POST.get('city')
        address.zone = request.POST.get('zone')
        address.is_default = bool(request.POST.get('is_default'))
        address.save()
        if address.is_default:
            ShippingAddress.objects.filter(user=request.user).exclude(pk=address.pk).update(is_default=False)
        messages.success(request, "Adresse modifiée.")
        return redirect('store:manage_addresses')
    return render(request, 'store/edit_address.html', {'address': address})

# Supprimer une adresse
@login_required
def delete_address(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Adresse supprimée.")
        return redirect('store:manage_addresses')
    return render(request, 'store/delete_address.html', {'address': address})

# Liste des commandes
@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_list.html', {'orders': orders})

# Détail commande
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    # Vérifier s'il y a un paiement en cours ou complété
    try:
        payment = order.payment_set.latest('created_at')
    except:
        payment = None
    
    return render(request, 'store/order_detail.html', {
        'order': order,
        'payment': payment
    })