from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delegates', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_paid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(choices=[('mpesa', 'M-Pesa'), ('cash', 'Cash')], max_length=10)),
                ('mpesa_transaction_id', models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ('status', models.CharField(choices=[('initiated', 'Initiated'), ('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed'), ('timeout', 'Timeout')], default='initiated', max_length=15)),
                ('entered_by_id', models.IntegerField(blank=True, null=True)),
                ('entered_by_name', models.CharField(blank=True, default='', max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('idempotency_key', models.CharField(max_length=128, unique=True)),
                ('delegate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='delegates.delegate')),
            ],
            options={'db_table': 'payments', 'ordering': ['timestamp']},
        ),
    ]