
import re
import shortuuid
import time
import phonenumbers
import time
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import User
from .models_countrycode import CountryCode
from store.models import Order, ShippingAddress
from django.contrib import messages
from django.db.models import Q

# ======================
# Utils
# ======================
def get_token_serializer():
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt='reset-password')

User = get_user_model()

def _generate_code():
    """Génère un code numérique court unique (6 caractères)."""
    return shortuuid.ShortUUID().random(length=6)

def _set_code_session(request, code_type):
    code = _generate_code()
    now = int(time.time())
    request.session[f'verify_{code_type}_code'] = code
    request.session[f'verify_{code_type}_code_time'] = now
    request.session[f'verify_{code_type}_regen_time'] = now + 300  # 5 min pour régénérer
    return code

def _can_regen_code(request, code_type):
    now = int(time.time())
    return now >= request.session.get(f'verify_{code_type}_regen_time', 0)

def _code_expired(request, code_type):
    now = int(time.time())
    code_time = request.session.get(f'verify_{code_type}_code_time', 0)
    return now - code_time > 900  # 15 min

# ======================
# Vues d'authentification
# ======================
@login_required
def livreur_dash(request):
    # Liste des commandes payées non expédiées
    commandes = Order.objects.filter(status='paid').order_by('-created_at')
    if request.method == 'POST':
        commande_id = request.POST.get('commande_id')
        commande = get_object_or_404(Order, pk=commande_id, status='paid')
        commande.status = 'expediee'
        commande.save()
        messages.success(request, f"Commande #{commande.id} marquée comme expédiée.")
        return redirect('store:livreur_dash')
    return render(request, 'store/livreur_dash.html', {'commandes': commandes})

def register_view(request):
    """Inscription utilisateur avec validation avancée et envoi des codes de vérification."""
    errors = {}
    data = {}
    global_error = ''
    country_codes = CountryCode.objects.filter(enabled=True).order_by('name')
    if request.method == 'POST':
        try:
            country_code = request.POST.get('country_code', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            data = {'country_code': country_code, 'phone': phone, 'email': email, 'first_name': first_name, 'last_name': last_name}
            # Validation avancée
            if not country_code:
                errors['phone'] = "Veuillez choisir un indicatif."
            if not phone:
                errors['phone'] = "Le numéro de téléphone est obligatoire."
            full_phone = f"{country_code}{phone}" if country_code and phone else ''
            if country_code and phone:
                try:
                    parsed = phonenumbers.parse(full_phone, None)
                    if not phonenumbers.is_valid_number(parsed):
                        errors['phone'] = "Numéro de téléphone invalide."
                except Exception:
                    errors['phone'] = "Numéro de téléphone invalide."
            if full_phone and User.objects.filter(phone=full_phone).exists():
                errors['phone'] = "Ce numéro est déjà utilisé."
            if not email:
                errors['email'] = "L'email est obligatoire."
            else:
                try:
                    validate_email(email)
                except ValidationError:
                    errors['email'] = "Adresse email invalide."
                if User.objects.filter(email=email).exists():
                    errors['email'] = "Cet email est déjà utilisé."
            if not first_name:
                errors['first_name'] = "Le prénom est obligatoire."
            if not last_name:
                errors['last_name'] = "Le nom est obligatoire."
            if not password1 or not password2:
                errors['password1'] = "Le mot de passe est obligatoire."
            elif password1 != password2:
                errors['password2'] = "Les mots de passe ne correspondent pas."
            else:
                if len(password1) < 8:
                    errors['password1'] = "Le mot de passe doit contenir au moins 8 caractères."
                if not re.search(r'[A-Z]', password1):
                    errors['password1'] = "Le mot de passe doit contenir au moins une majuscule."
                if not re.search(r'[a-z]', password1):
                    errors['password1'] = "Le mot de passe doit contenir au moins une minuscule."
                if not re.search(r'\d', password1):
                    errors['password1'] = "Le mot de passe doit contenir au moins un chiffre."
                if not re.search(r'[^A-Za-z0-9]', password1):
                    errors['password1'] = "Le mot de passe doit contenir au moins un caractère spécial."
            if not errors:
                user = User.objects.create_user(
                    phone=full_phone,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password1,
                )
                request.session['verify_user_id'] = user.id
                # Génère et envoie le code phone (shortuuid, 6 chiffres)
                code = _set_code_session(request, 'phone')
                print(f"[SMS] Code de vérification pour {user.phone} : {code}")
                return redirect('verify_phone')
        except Exception as e:
            global_error = "Une erreur technique est survenue. Merci de réessayer plus tard."
    return render(request, 'users/register.html', {'errors': errors, 'data': data, 'country_codes': country_codes})





def verify_phone_view(request):
    errors = {}
    global_error = ''
    if not request.session.get('verify_user_id'):
        return redirect('login')
    user_id = request.session['verify_user_id']
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('login')
    # Génération du code si besoin
    if not request.session.get('verify_phone_code') or _code_expired(request, 'phone'):
        code = _set_code_session(request, 'phone')
        # Ici, envoyer le code par SMS (mock print)
        print(f"[SMS] Code de vérification pour {user.phone} : {code}")
    if request.method == 'POST':
        if 'regen_code' in request.POST:
            if _can_regen_code(request, 'phone'):
                code = _set_code_session(request, 'phone')
                print(f"[SMS] Nouveau code pour {user.phone} : {code}")
            else:
                errors['regen'] = "Vous pouvez régénérer un code toutes les 5 minutes."
        else:
            code = request.POST.get('phone_code', '').strip()
            if not code:
                errors['phone_code'] = "Code requis."
            elif _code_expired(request, 'phone'):
                errors['phone_code'] = "Code expiré. Cliquez sur régénérer."
            elif code != request.session.get('verify_phone_code'):
                errors['phone_code'] = "Code incorrect."
            if not errors:
                user.is_phone_verified = True
                user.save()
                # Nettoyer la session du code phone
                for k in ['verify_phone_code', 'verify_phone_code_time', 'verify_phone_regen_time']:
                    if k in request.session:
                        del request.session[k]
                # Passer à la vérification email si besoin
                if not user.is_email_verified:
                    request.session['verify_user_id'] = user.id
                    return redirect('verify_email')
                login(request, user)
                return redirect('store:home')
    can_regen = _can_regen_code(request, 'phone')
    return render(request, 'users/verify_phone.html', {'errors': errors, 'global_error': global_error, 'can_regen': can_regen})

def verify_email_view(request):
    errors = {}
    global_error = ''
    if not request.session.get('verify_user_id'):
        return redirect('login')
    user_id = request.session['verify_user_id']
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('login')
    # Génération du code si besoin
    if not request.session.get('verify_email_code') or _code_expired(request, 'email'):
        code = _set_code_session(request, 'email')
        # Envoyer le code par email
        send_mail(
            'Code de vérification email',
            f'Votre code de vérification est : {code}',
            'noreply@wooditech.local',  # Utilisation directe du from email
            [user.email],
        )
    if request.method == 'POST':
        if 'regen_code' in request.POST:
            if _can_regen_code(request, 'email'):
                code = _set_code_session(request, 'email')
                send_mail(
                    'Nouveau code de vérification email',
                    f'Votre nouveau code est : {code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
            else:
                errors['regen'] = "Vous pouvez régénérer un code toutes les 5 minutes."
        else:
            code = request.POST.get('email_code', '').strip()
            if not code:
                errors['email_code'] = "Code requis."
            elif _code_expired(request, 'email'):
                errors['email_code'] = "Code expiré. Cliquez sur régénérer."
            elif code != request.session.get('verify_email_code'):
                errors['email_code'] = "Code incorrect."
            if not errors:
                user.is_email_verified = True
                user.save()
                # Nettoyer la session du code email
                for k in ['verify_email_code', 'verify_email_code_time', 'verify_email_regen_time', 'verify_user_id']:
                    if k in request.session:
                        del request.session[k]
                # Spécifie explicitement le backend pour éviter l'erreur ValueError
                from django.conf import settings
                backend = settings.AUTHENTICATION_BACKENDS[0]
                user.backend = backend
                login(request, user, backend=backend)
                return redirect('store:home')
    can_regen = _can_regen_code(request, 'email')
    return render(request, 'users/verify_email.html', {'errors': errors, 'global_error': global_error, 'can_regen': can_regen})

def login_view(request):
    """Connexion utilisateur avec limitation de tentatives."""
    errors = {}
    data = {}
    max_attempts = 5
    block_minutes = 5
    from datetime import datetime, timedelta
    
    blocked_until = request.session.get('login_blocked_until')
    now = datetime.now().timestamp()
    if blocked_until and now < blocked_until:
        errors['non_field'] = f"Trop de tentatives. Réessayez dans {int((blocked_until-now)//60)+1} minutes."
        return render(request, 'users/login.html', {'errors': errors, 'data': {}})
    
    country_codes = CountryCode.objects.filter(enabled=True).order_by('name')
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        country_code = request.POST.get('country_code', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        data['identifier'] = identifier
        data['country_code'] = country_code
        data['phone'] = phone
        if not identifier and not (country_code and phone):
            errors['identifier'] = "Renseignez l'email ou le numéro."
        if not password:
            errors['password'] = "Le mot de passe est obligatoire."
        user = None
        if not errors:
            if country_code and phone:
                full_phone = f"{country_code}{phone}"
                user = authenticate(phone=full_phone, password=password)
            elif identifier:
                user = authenticate(email=identifier, password=password)
            if not user:
                # Gestion des tentatives
                attempts = request.session.get('login_attempts', 0) + 1
                request.session['login_attempts'] = attempts
                if attempts >= max_attempts:
                    request.session['login_blocked_until'] = (datetime.now() + timedelta(minutes=block_minutes)).timestamp()
                    errors['non_field'] = f"Trop de tentatives. Réessayez dans {block_minutes} minutes."
                else:
                    errors['non_field'] = f"Identifiants invalides. Tentative {attempts}/{max_attempts}."
            else:
                # Succès : reset le compteur
                request.session['login_attempts'] = 0
        if not errors and user:
            # Vérification stricte : numéro et email doivent être vérifiés
            if not user.is_phone_verified:
                request.session['verify_user_id'] = user.id
                return redirect('verify_phone')
            if not user.is_email_verified:
                request.session['verify_user_id'] = user.id
                return redirect('verify_email')
            login(request, user)
            # Redirection selon le rôle
            if user.role == 'admin':
                return redirect('store:admin_dashboard')
            elif user.role == 'livreur':
                return redirect('store:livreur_dashboard')
            else:
                return redirect('store:home')
        return render(request, 'users/login.html', {'errors': errors, 'data': data, 'country_codes': country_codes})
    return render(request, 'users/login.html', {'errors': errors, 'data': data, 'country_codes': country_codes})

def logout_view(request):
    """Déconnexion utilisateur."""
    logout(request)
    return redirect('login')

@login_required
def password_change_view(request):
    """Changement de mot de passe pour utilisateur connecté."""
    errors = {}
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')
        # Validation
        if not old_password:
            errors['old_password'] = "L'ancien mot de passe est obligatoire."
        elif not request.user.check_password(old_password):
            errors['old_password'] = "Ancien mot de passe incorrect."
        if not new_password1:
            errors['new_password1'] = "Le nouveau mot de passe est obligatoire."
        elif len(new_password1) < 8:
            errors['new_password1'] = "Le mot de passe doit contenir au moins 8 caractères."
        if not new_password2:
            errors['new_password2'] = "Veuillez confirmer le nouveau mot de passe."
        elif new_password1 and new_password1 != new_password2:
            errors['new_password2'] = "Les nouveaux mots de passe ne correspondent pas."
        if not errors:
            request.user.set_password(new_password1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            return redirect('login')
        return render(request, 'users/password_change.html', {'errors': errors})
    return render(request, 'users/password_change.html', {'errors': errors})


def forgot_password_view(request):
    """Demande de réinitialisation de mot de passe (envoi d'un lien par email)."""
    errors = {}
    data = {}
    message = ''
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        data['identifier'] = identifier
        user = None
        if not identifier:
            errors['identifier'] = "Ce champ est obligatoire."
        else:
            try:
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(phone=identifier)
            except User.DoesNotExist:
                errors['identifier'] = "Aucun utilisateur trouvé avec cet identifiant."
        if not errors and user:
            # Générer un token sécurisé avec expiration (30 min)
            s = get_token_serializer()
            token = s.dumps({'user_id': user.id})
            # Envoyer le lien par email si email existe
            if user.email:
                reset_url = request.build_absolute_uri(f"/auth/reset-password/{token}/")
                send_mail(
                    'Réinitialisation de votre mot de passe',
                    f'Cliquez sur ce lien pour réinitialiser votre mot de passe : {reset_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
            message = "Un lien de réinitialisation a été envoyé."
        return render(request, 'users/forgot_password.html', {'errors': errors, 'data': data, 'message': message})
    return render(request, 'users/forgot_password.html', {'errors': errors, 'data': data, 'message': message})

def reset_password_view(request, token):
    """Réinitialisation du mot de passe via un lien sécurisé."""
    errors = {}
    user = None
    token_valid = True
    s = get_token_serializer()
    try:
        data = s.loads(token, max_age=900)  # 30 minutes
        user_id = data.get('user_id')
        user = User.objects.get(id=user_id)
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        errors['non_field'] = "Lien invalide ou expiré. Veuillez refaire une demande de réinitialisation."
        user = None
        token_valid = False
    if request.method == 'POST' and user:
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')
        if not new_password1:
            errors['new_password1'] = "Le nouveau mot de passe est obligatoire."
        elif len(new_password1) < 8:
            errors['new_password1'] = "Le mot de passe doit contenir au moins 8 caractères."
        if not new_password2:
            errors['new_password2'] = "Veuillez confirmer le nouveau mot de passe."
        elif new_password1 and new_password1 != new_password2:
            errors['new_password2'] = "Les nouveaux mots de passe ne correspondent pas."
        if not errors:
            user.set_password(new_password1)
            user.save()
            return redirect('login')
    return render(request, 'users/reset_password.html', {'errors': errors, 'token': token, 'token_valid': token_valid})

