from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('conventions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delegate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delegate_id', models.CharField(blank=True, default='', max_length=30, unique=True)),
                ('full_name', models.CharField(max_length=100)),
                ('category', models.CharField(choices=[('student', 'Student'), ('kessat', 'Kessat'), ('associate', 'Associate')], max_length=15)),
                ('parent_name', models.CharField(max_length=100)),
                ('parent_phone', models.CharField(max_length=20)),
                ('email', models.EmailField()),
                ('registration_status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active')], default='pending', max_length=10)),
                ('qr_code_path', models.CharField(blank=True, default='', max_length=255)),
                ('registration_date', models.DateTimeField(auto_now_add=True)),
                ('registered_by_id', models.IntegerField(blank=True, null=True)),
                ('county', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delegates', to='conventions.county')),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='delegates', to='conventions.convention')),
            ],
            options={'db_table': 'delegates', 'unique_together': {('email', 'convention')}},
        ),
        migrations.CreateModel(
            name='WriteOff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_written_off', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reason', models.TextField()),
                ('written_off_by_id', models.IntegerField()),
                ('written_off_by_name', models.CharField(max_length=100)),
                ('written_off_at', models.DateTimeField(auto_now_add=True)),
                ('totp_confirmed', models.BooleanField(default=False)),
                ('delegate', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='write_offs', to='delegates.delegate')),
                ('convention_unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='write_offs', to='conventions.conventionunit')),
            ],
            options={'db_table': 'write_offs'},
        ),
    ]