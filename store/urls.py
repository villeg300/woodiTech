from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:pk>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/apply-promo/', views.apply_promo, name='apply_promo'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    # Address management
    path('addresses/', views.manage_addresses, name='manage_addresses'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/<int:pk>/edit/', views.edit_address, name='edit_address'),
    path('addresses/<int:pk>/delete/', views.delete_address, name='delete_address'),
    # Admin dashboard & CRUD
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_product_list, name='admin_product_list'),
    path('admin/products/add/', views.admin_add_product, name='admin_add_product'),
    path('admin/products/<int:pk>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('admin/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('admin/livreurs/', views.admin_livreur_list, name='admin_livreur_list'),
    path('admin/livreurs/add/', views.admin_add_livreur, name='admin_add_livreur'),
    path('admin/livreurs/<int:pk>/edit/', views.admin_edit_livreur, name='admin_edit_livreur'),
    path('admin/livreurs/<int:pk>/delete/', views.admin_delete_livreur, name='admin_delete_livreur'),
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/orders/', views.admin_order_list, name='admin_order_list'),
    # Recherche produit admin
    path('admin/products/search/', views.admin_product_search, name='admin_product_search'),

    # Espace livreur
    path('livreur/dashboard/', views.livreur_dashboard, name='livreur_dashboard'),

    # CRUD catégories
    path('admin/categories/', views.admin_category_list, name='admin_category_list'),
    path('admin/categories/add/', views.admin_add_category, name='admin_add_category'),
    path('admin/categories/<int:pk>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('admin/categories/<int:pk>/delete/', views.admin_delete_category, name='admin_delete_category'),

    # Produits par catégorie
    path('categories/<int:pk>/products/', views.category_products, name='category_products'),
]
