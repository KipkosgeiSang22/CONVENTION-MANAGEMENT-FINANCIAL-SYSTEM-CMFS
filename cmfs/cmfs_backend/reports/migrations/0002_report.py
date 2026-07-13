from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
        ('conventions', '0003_convention_lifecycle_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('opening_day', 'Opening Day'), ('final', 'Final')], max_length=20)),
                ('format', models.CharField(choices=[('xlsx', 'Excel'), ('pdf', 'PDF')], max_length=10)),
                ('file_path', models.CharField(blank=True, default='', max_length=500)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('generated', 'Generated'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('error_message', models.TextField(blank=True, default='')),
                ('generated_by_id', models.IntegerField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='conventions.convention')),
                ('convention_unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='conventions.conventionunit')),
            ],
            options={'db_table': 'reports', 'ordering': ['-created_at']},
        ),
    ]
