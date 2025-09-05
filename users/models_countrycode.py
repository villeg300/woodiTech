from django.db import models

class CountryCode(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=8, unique=True)  # ex: +33
    iso = models.CharField(max_length=2, unique=True)   # ex: FR
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Indicatif pays'
        verbose_name_plural = 'Indicatifs pays'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"
