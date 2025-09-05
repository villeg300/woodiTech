from django.urls import path


from . import views


urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),
    path('verify-phone/', views.verify_phone_view, name='verify_phone'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('livreur-dash/', views.livreur_dash, name='livreur_dash'),
]
