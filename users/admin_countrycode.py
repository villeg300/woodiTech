from django.contrib import admin
from .models_countrycode import CountryCode

@admin.register(CountryCode)
class CountryCodeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "iso", "enabled")
    list_filter = ("enabled",)
    search_fields = ("name", "code", "iso")
