from django.db import models


class Delegate(models.Model):
    CATEGORY_CHOICES = [
        ('student', 'Student'),
        ('kessat', 'Kessat'),
        ('associate', 'Associate'),
    ]
    REGISTRATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
    ]

    # e.g. KER-STU-2025-0042 — generated on first confirmed payment.
    # null=True (not default='') is required: every PENDING delegate has no
    # delegate_id yet, and a unique constraint treats repeated '' values as
    # a collision (unlike NULL, which is allowed to repeat) — with
    # default='' the *second* delegate ever created (any email, any
    # convention) fails IntegrityError on this field, not on email.
    delegate_id = models.CharField(max_length=30, unique=True, blank=True, null=True, default=None)
    full_name = models.CharField(max_length=100)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=20)  # normalised to 2547XXXXXXXX
    email = models.EmailField()
    county = models.ForeignKey(
        'conventions.County',
        on_delete=models.PROTECT,
        related_name='delegates'
    )
    convention = models.ForeignKey(
        'conventions.Convention',
        on_delete=models.PROTECT,
        related_name='delegates'
    )
    registration_status = models.CharField(
        max_length=10,
        choices=REGISTRATION_STATUS_CHOICES,
        default='pending'
    )
    qr_code_path = models.CharField(max_length=255, blank=True, default='')
    registration_date = models.DateTimeField(auto_now_add=True)
    registered_by_id = models.IntegerField(null=True, blank=True)  # null = self-registered

    class Meta:
        db_table = 'delegates'
        # Unique email per convention
        unique_together = [('email', 'convention')]

    def __str__(self):
        return f"{self.full_name} — {self.delegate_id or 'PENDING'}"

    # ── Category code (Phase 6) ─────────────────────────────────────────────
    CATEGORY_CODES = {'student': 'STU', 'kessat': 'KES', 'associate': 'ASC'}

    @property
    def category_code(self) -> str:
        return self.CATEGORY_CODES.get(self.category, 'UNK')

    # ── Fee / payment status (derived, never stored) ────────────────────────

    @property
    def fee_amount(self):
        """The convention's fee schedule for this delegate's category."""
        field = {'student': 'fee_student', 'kessat': 'fee_kessat', 'associate': 'fee_associate'}[self.category]
        return getattr(self.convention, field)

    @property
    def total_paid(self):
        from django.db.models import Sum
        total = self.payments.filter(status='confirmed').aggregate(total=Sum('amount_paid'))['total']
        return total or 0

    @property
    def balance_owed(self):
        return self.fee_amount - self.total_paid

    @property
    def payment_status(self) -> str:
        """PENDING | NOT_PAID | INCOMPLETE | COMPLETE | OVERPAID"""
        if self.registration_status == 'pending':
            return 'PENDING'
        paid = self.total_paid
        fee = self.fee_amount
        if paid <= 0:
            return 'NOT_PAID'
        if paid < fee:
            return 'INCOMPLETE'
        if paid > fee:
            return 'OVERPAID'
        return 'COMPLETE'


class WriteOff(models.Model):
    delegate = models.ForeignKey(Delegate, on_delete=models.PROTECT, related_name='write_offs')
    convention_unit = models.ForeignKey(
        'conventions.ConventionUnit',
        on_delete=models.PROTECT,
        related_name='write_offs'
    )
    amount_written_off = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()  # required — enforced at API level
    written_off_by_id = models.IntegerField()
    written_off_by_name = models.CharField(max_length=100)  # from JWT
    written_off_at = models.DateTimeField(auto_now_add=True)
    totp_confirmed = models.BooleanField(default=False)  # must be True — enforced at API level

    class Meta:
        db_table = 'write_offs'

    def __str__(self):
        return f"WriteOff — {self.delegate} — KES {self.amount_written_off}"