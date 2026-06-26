from django.db import models


class Payment(models.Model):
    METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
    ]
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]

    delegate = models.ForeignKey(
        'delegates.Delegate',
        on_delete=models.PROTECT,
        related_name='payments'
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    mpesa_transaction_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='initiated')
    entered_by_id = models.IntegerField(null=True, blank=True)    # from JWT; null for self-service
    entered_by_name = models.CharField(max_length=100, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    idempotency_key = models.CharField(max_length=128, unique=True)

    class Meta:
        db_table = 'payments'
        ordering = ['timestamp']

    def __str__(self):
        return f"Payment {self.id} — {self.delegate} — {self.amount_paid} ({self.status})"