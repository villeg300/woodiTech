

# Initialisation Django pour script standalone
import os
import sys
import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models_countrycode import CountryCode

# Liste d'exemples d'indicatifs à ajouter (vous pouvez compléter ou modifier)
COUNTRY_CODES = [
    {"name": "Burkina Faso", "code": "+226", "iso": "BF"},
]

def create_country_codes():
    for entry in COUNTRY_CODES:
        obj, created = CountryCode.objects.get_or_create(
            code=entry["code"],
            defaults={"name": entry["name"], "iso": entry["iso"], "enabled": True}
        )
        if created:
            print(f"Ajouté: {obj}")
        else:
            print(f"Déjà présent: {obj}")

if __name__ == "__main__":
    create_country_codes()
