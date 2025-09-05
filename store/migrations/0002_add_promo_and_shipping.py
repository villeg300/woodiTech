# Generated manually

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('min_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('valid_from', models.DateTimeField(default=django.utils.timezone.now)),
                ('valid_until', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('usage_limit', models.PositiveIntegerField(default=0)),
                ('times_used', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0.00, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_fee',
            field=models.DecimalField(decimal_places=2, default=0.00, max_digits=10),
        ),
        migrations.AddField(
            model_name='order',
            name='promo_code',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.promocode'),
        ),
    ]
