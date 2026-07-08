"""
FILE: cmfs/cmfs_backend/conventions/models.py
ACTION: REPLACE (Phase 3)
CHANGES:
  - Convention model: added scope_locked_at, published_at, started_at, ended_at,
    financially_closed_at, archived_at lifecycle timestamps
  - ConventionUnit: added county and region FK references, display helpers
  - Added __str__ improvements
"""

from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'regions'
        ordering = ['name']

    def __str__(self):
        return self.name


class County(models.Model):
    name = models.CharField(max_length=100, unique=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='counties')
    county_code = models.CharField(max_length=3, unique=True)  # e.g. KER, NBI

    class Meta:
        db_table = 'counties'
        ordering = ['name']
        verbose_name_plural = 'counties'

    def __str__(self):
        return f"{self.name} ({self.county_code})"


class Convention(models.Model):
    SCOPE_COUNTY = 'county'
    SCOPE_REGIONAL = 'regional'
    SCOPE_NATIONAL = 'national'
    SCOPE_CHOICES = [
        (SCOPE_COUNTY, 'County'),
        (SCOPE_REGIONAL, 'Regional'),
        (SCOPE_NATIONAL, 'National'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_OPEN = 'open'
    STATUS_ACTIVE = 'active'
    STATUS_ENDED = 'ended'
    STATUS_FINANCIALLY_CLOSED = 'financially_closed'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_OPEN, 'Open'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ENDED, 'Ended'),
        (STATUS_FINANCIALLY_CLOSED, 'Financially Closed'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    # Core fields
    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, default='')

    # Fees — locked permanently when DRAFT → OPEN
    fee_student = models.DecimalField(max_digits=10, decimal_places=2)
    fee_kessat = models.DecimalField(max_digits=10, decimal_places=2)
    fee_associate = models.DecimalField(max_digits=10, decimal_places=2)

    # Status & control flags
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_registration_open = models.BooleanField(default=False)
    scope_locked = models.BooleanField(default=False)  # True once DRAFT→OPEN

    # Lifecycle timestamps
    scope_locked_at = models.DateTimeField(null=True, blank=True)   # when scope was permanently locked
    published_at = models.DateTimeField(null=True, blank=True)       # DRAFT → OPEN
    started_at = models.DateTimeField(null=True, blank=True)         # OPEN/DRAFT → ACTIVE
    ended_at = models.DateTimeField(null=True, blank=True)           # ACTIVE → ENDED
    financially_closed_at = models.DateTimeField(null=True, blank=True)  # ENDED → FINANCIALLY_CLOSED
    archived_at = models.DateTimeField(null=True, blank=True)        # → ARCHIVED

    # Audit
    created_by_id = models.IntegerField(null=True, blank=True)      # user id from JWT
    financially_closed_by_id = models.IntegerField(null=True, blank=True)  # user id from JWT
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conventions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.scope}] ({self.status})"

    @property
    def is_editable(self):
        """Only DRAFT conventions are fully editable."""
        return self.status == self.STATUS_DRAFT

    @property
    def gate_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def can_enter_expenses(self):
        return self.status in (self.STATUS_ACTIVE, self.STATUS_ENDED)

    @property
    def is_read_only(self):
        return self.status in (self.STATUS_FINANCIALLY_CLOSED, self.STATUS_ARCHIVED)


class ConventionUnit(models.Model):
    SCOPE_TYPE_CHOICES = [
        ('county', 'County'),
        ('regional', 'Regional'),
        ('national', 'National'),
    ]

    convention = models.ForeignKey(Convention, on_delete=models.PROTECT, related_name='units')
    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPE_CHOICES)

    # Nullable FKs — only one will be set depending on scope_type
    county = models.ForeignKey(
        County,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='convention_units',
    )
    region = models.ForeignKey(
        Region,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='convention_units',
    )

    # Kept for backwards-compat with Phase 2 code that used raw int
    scope_id = models.IntegerField(null=True, blank=True)

    # Head user assigned to this unit (foreign key by id only — avoids circular import)
    head_user_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = 'convention_units'
        unique_together = [('convention', 'scope_type', 'scope_id')]

    def __str__(self):
        if self.county:
            return f"{self.convention.name} — {self.county.name}"
        if self.region:
            return f"{self.convention.name} — {self.region.name}"
        return f"{self.convention.name} — National"

    @property
    def display_name(self):
        if self.county:
            return self.county.name
        if self.region:
            return self.region.name
        return 'National'