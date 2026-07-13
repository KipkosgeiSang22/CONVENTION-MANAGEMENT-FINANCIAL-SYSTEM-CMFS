from django.db import models


class Report(models.Model):
    """
    FILE: cmfs/cmfs_backend/reports/models.py
    ACTION: UPDATE (Phase 10)

    One row per generated report file. `convention_unit = NULL` means the
    overall/consolidated report for the whole convention (see Phase 10 spec).
    """
    REPORT_TYPE_CHOICES = [
        ('opening_day', 'Opening Day'),
        ('final', 'Final'),
    ]
    FORMAT_CHOICES = [
        ('xlsx', 'Excel'),
        ('pdf', 'PDF'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
    ]

    convention = models.ForeignKey(
        'conventions.Convention', on_delete=models.CASCADE, related_name='reports'
    )
    convention_unit = models.ForeignKey(
        'conventions.ConventionUnit', null=True, blank=True,
        on_delete=models.CASCADE, related_name='reports',
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    file_path = models.CharField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    generated_by_id = models.IntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        constraints = [
            # One row per (convention, unit, report_type, format) slot.
            # convention_unit is nullable (NULL = overall/consolidated
            # report), and Postgres treats every NULL as distinct under a
            # normal unique_together — so that needs its own partial
            # index, split out from the non-NULL case below. Without this,
            # re-generating reports (dev "Generate Reports Now", a second
            # financial-close retry, opening day re-triggered) can leave
            # multiple rows for the same slot, which showed up as
            # duplicated Download buttons on the convention detail page.
            models.UniqueConstraint(
                fields=['convention', 'report_type', 'format'],
                condition=models.Q(convention_unit__isnull=True),
                name='uniq_report_overall_slot',
            ),
            models.UniqueConstraint(
                fields=['convention', 'convention_unit', 'report_type', 'format'],
                condition=models.Q(convention_unit__isnull=False),
                name='uniq_report_unit_slot',
            ),
        ]

    def __str__(self):
        scope = self.convention_unit.display_name if self.convention_unit_id else 'OVERALL'
        return f"Report — {self.convention.name} — {scope} — {self.report_type}.{self.format}"


class AnnualSummary(models.Model):
    """
    FILE: cmfs/cmfs_backend/reports/models.py
    ACTION: UPDATE (Phase 11)

    One row per calendar year. Generated automatically 7 days after a
    December convention reaches FINANCIALLY_CLOSED (see
    conventions.tasks.check_annual_summary_trigger), or on-demand by
    Super Admin. Aggregates every FINANCIALLY_CLOSED convention whose
    end_date falls in `year` — see reports.generators.aggregate_annual_summary.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
    ]

    year = models.IntegerField(unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    xlsx_path = models.CharField(max_length=500, blank=True, default='')
    pdf_path = models.CharField(max_length=500, blank=True, default='')
    # Small rollup of headline totals (total_income, total_expenditure,
    # total_delegates) — kept alongside the full report so next year's
    # year-on-year comparison doesn't need to re-aggregate this year's data.
    summary_totals = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    triggered_by_id = models.IntegerField(null=True, blank=True)  # null = automatic/system trigger
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'annual_summaries'
        ordering = ['-year']

    def __str__(self):
        return f"AnnualSummary — {self.year} ({self.status})"


class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=100, blank=True, default='')
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100, blank=True, default='')
    record_id = models.IntegerField(null=True, blank=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        # No update or delete — enforced via RLS (see migration SQL below)

    def __str__(self):
        return f"AuditLog — {self.action} by {self.user_name} at {self.timestamp}"