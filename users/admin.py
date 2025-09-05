
from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from .admin_countrycode import *


# --- Forms ---
class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmer le mot de passe', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('phone', 'email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_phone_verified')

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = (
            'phone', 'email', 'first_name', 'last_name', 'role', 'password',
            'is_active', 'is_staff', 'is_email_verified', 'is_phone_verified',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# --- Admin ---
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = (
        'phone', 'email', 'first_name', 'last_name', 'role',
        'is_active', 'is_staff', 'is_email_verified', 'is_phone_verified'
    )
    search_fields = ('phone', 'email', 'first_name', 'last_name')
    list_filter = ('role', 'is_active', 'is_staff', 'is_email_verified', 'is_phone_verified')
    ordering = ('phone',)
    readonly_fields = ('date_joined',)
    fieldsets = (
        (None, {
            'fields': (
                'phone', 'email', 'first_name', 'last_name', 'role', 'password',
                'is_email_verified', 'is_phone_verified',
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone', 'email', 'first_name', 'last_name', 'role',
                'password1', 'password2',
                'is_active', 'is_staff', 'is_superuser',
                'is_email_verified', 'is_phone_verified',
            )
        }),
    )

# Register your models here.
