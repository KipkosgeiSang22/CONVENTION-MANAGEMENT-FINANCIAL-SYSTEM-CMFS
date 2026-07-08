"""
FILE: cmfs/cmfs_backend/delegates/migrations/0002_fix_delegate_id_null.py
ACTION: CREATE

Fixes the delegate_id unique+default='' collision: every PENDING delegate
(no delegate_id assigned yet) was getting default='', and a unique
constraint treats repeated '' values as a collision (NULL is exempt from
this in Postgres/SQLite). That meant the *second* delegate ever created —
regardless of email — hit an IntegrityError, which the view code then
misreported as "Email already registered."

RunPython step: any existing rows already stored as '' are converted to
NULL so they don't collide with each other going forward.
"""

from django.db import migrations, models


def blank_to_null(apps, schema_editor):
    Delegate = apps.get_model('delegates', 'Delegate')
    Delegate.objects.filter(delegate_id='').update(delegate_id=None)


def null_to_blank(apps, schema_editor):
    Delegate = apps.get_model('delegates', 'Delegate')
    Delegate.objects.filter(delegate_id__isnull=True).update(delegate_id='')


class Migration(migrations.Migration):

    dependencies = [
        ('delegates', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(blank_to_null, null_to_blank),
        migrations.AlterField(
            model_name='delegate',
            name='delegate_id',
            field=models.CharField(blank=True, default=None, max_length=30, null=True, unique=True),
        ),
    ]