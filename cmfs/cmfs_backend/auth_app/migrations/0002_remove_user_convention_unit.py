from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0001_initial'),
        ('conventions', '0003_convention_lifecycle_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='convention_unit',
        ),
    ]
