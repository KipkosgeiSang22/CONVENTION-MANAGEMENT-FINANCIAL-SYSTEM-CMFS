from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delegates', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checked_in', models.BooleanField(default=False)),
                ('checked_in_at', models.DateTimeField(blank=True, null=True)),
                ('checked_in_by_id', models.IntegerField(blank=True, null=True)),
                ('checked_in_by_name', models.CharField(blank=True, default='', max_length=100)),
                ('gate_location', models.CharField(blank=True, default='', max_length=100)),
                ('cash_collected_at_gate', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('payment_completed_at_gate', models.BooleanField(default=False)),
                ('synced_from_offline', models.BooleanField(default=False)),
                ('delegate', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='attendance', to='delegates.delegate')),
            ],
            options={'db_table': 'attendance'},
        ),
    ]