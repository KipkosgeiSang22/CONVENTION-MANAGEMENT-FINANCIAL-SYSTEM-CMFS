from django.db import migrations, models


def dedupe_reports(apps, schema_editor):
    """
    Pre-existing installs may have accumulated duplicate Report rows for
    the same (convention, convention_unit, report_type, format) slot —
    from before _generate_single switched to update_or_create, re-running
    the dev "Generate Reports Now" button, overlapping generation calls,
    etc. Keep only the most recently created row per slot (the one
    actually pointing at the current file on disk — see
    reports.generators._generate_single, file paths are deterministic per
    slot, so the newest row is always the one matching what's on disk)
    and delete the rest, so the unique constraints added below can apply.
    """
    Report = apps.get_model('reports', 'Report')

    seen = {}
    for report in Report.objects.order_by('created_at', 'id'):
        key = (report.convention_id, report.convention_unit_id, report.report_type, report.format)
        seen[key] = report.id  # last write wins -> keeps the newest row's id

    keep_ids = set(seen.values())
    Report.objects.exclude(id__in=keep_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_annual_summary'),
    ]

    operations = [
        migrations.RunPython(dedupe_reports, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='report',
            constraint=models.UniqueConstraint(
                fields=['convention', 'report_type', 'format'],
                condition=models.Q(convention_unit__isnull=True),
                name='uniq_report_overall_slot',
            ),
        ),
        migrations.AddConstraint(
            model_name='report',
            constraint=models.UniqueConstraint(
                fields=['convention', 'convention_unit', 'report_type', 'format'],
                condition=models.Q(convention_unit__isnull=False),
                name='uniq_report_unit_slot',
            ),
        ),
    ]
