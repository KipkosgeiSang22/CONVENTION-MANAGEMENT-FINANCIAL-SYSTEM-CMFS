from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.IntegerField(blank=True, null=True)),
                ('user_name', models.CharField(blank=True, default='', max_length=100)),
                ('action', models.CharField(max_length=100)),
                ('table_name', models.CharField(blank=True, default='', max_length=100)),
                ('record_id', models.IntegerField(blank=True, null=True)),
                ('previous_value', models.JSONField(blank=True, null=True)),
                ('new_value', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
            ],
            options={'db_table': 'audit_logs', 'ordering': ['-timestamp']},
        ),
    ]