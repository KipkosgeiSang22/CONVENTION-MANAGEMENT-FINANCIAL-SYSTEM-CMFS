from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_report'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnualSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField(unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('generated', 'Generated'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('xlsx_path', models.CharField(blank=True, default='', max_length=500)),
                ('pdf_path', models.CharField(blank=True, default='', max_length=500)),
                ('summary_totals', models.JSONField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, default='')),
                ('triggered_by_id', models.IntegerField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'annual_summaries', 'ordering': ['-year']},
        ),
    ]
