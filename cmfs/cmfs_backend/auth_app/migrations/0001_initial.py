from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('conventions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=100)),
                ('email', models.EmailField(unique=True)),
                ('phone', models.CharField(blank=True, default='', max_length=20)),
                ('role', models.CharField(choices=[('super_admin', 'Super Admin'), ('national_head', 'National Head'), ('regional_head', 'Regional Head'), ('county_head', 'County Head'), ('budget_creator', 'Budget Creator'), ('finance_viewer', 'Finance Viewer'), ('gate_official', 'Gate Official'), ('delegate', 'Delegate')], max_length=20)),
                ('password_hash', models.CharField(max_length=255)),
                ('totp_secret', models.CharField(blank=True, default='', max_length=64)),
                ('totp_enabled', models.BooleanField(default=False)),
                ('token_version', models.IntegerField(default=0)),
                ('setup_token', models.CharField(blank=True, default='', max_length=128)),
                ('setup_token_expires_at', models.DateTimeField(blank=True, null=True)),
                ('failed_login_attempts', models.IntegerField(default=0)),
                ('locked_until', models.DateTimeField(blank=True, null=True)),
                ('last_login_at', models.DateTimeField(blank=True, null=True)),
                ('last_login_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('convention_unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='conventions.conventionunit')),
                ('county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='conventions.county')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='conventions.region')),
            ],
            options={'db_table': 'users'},
        ),
        migrations.CreateModel(
            name='RecoveryCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=255)),
                ('used', models.BooleanField(default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_codes', to='auth_app.user')),
            ],
            options={'db_table': 'recovery_codes'},
        ),
    ]