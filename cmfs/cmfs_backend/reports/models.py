from django.db import models


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