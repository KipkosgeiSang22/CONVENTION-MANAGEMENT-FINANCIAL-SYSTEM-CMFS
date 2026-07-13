from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0002_add_appr_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetincome',
            name='actual_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]