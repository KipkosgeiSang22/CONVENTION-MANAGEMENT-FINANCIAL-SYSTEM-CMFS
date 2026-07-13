"""
FILE: cmfs/cmfs_backend/delegates/migrations/0003_delegate_chase_status.py
ACTION: CREATE (Phase 9)

Adds chase_status + chase_requested_at to Delegate, for the "Chase
payment" action (POST /api/delegates/{id}/chase/).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delegates', '0002_fix_delegate_id_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='delegate',
            name='chase_status',
            field=models.CharField(
                choices=[('none', 'None'), ('pending_chase', 'Pending Chase')],
                default='none', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='delegate',
            name='chase_requested_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
