from django.core.management.base import BaseCommand
from django.utils import timezone
from store.models import PromoCode

class Command(BaseCommand):
    help = 'Nettoie les codes promo expirés'

    def handle(self, *args, **options):
        # Supprime les codes promo expirés
        deleted_count = PromoCode.objects.filter(
            valid_until__lt=timezone.now()
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} expired promo codes')
        )
