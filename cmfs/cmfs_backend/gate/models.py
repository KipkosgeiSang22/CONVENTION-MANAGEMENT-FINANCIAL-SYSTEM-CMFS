from django.db import models


class Attendance(models.Model):
    delegate = models.OneToOneField(
        'delegates.Delegate',
        on_delete=models.PROTECT,
        related_name='attendance'
    )
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by_id = models.IntegerField(null=True, blank=True)   # from JWT
    checked_in_by_name = models.CharField(max_length=100, blank=True, default='')  # from JWT
    gate_location = models.CharField(max_length=100, blank=True, default='')
    cash_collected_at_gate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    payment_completed_at_gate = models.BooleanField(default=False)
    synced_from_offline = models.BooleanField(default=False)

    class Meta:
        db_table = 'attendance'

    def __str__(self):
        return f"Attendance — {self.delegate} — checked_in={self.checked_in}"