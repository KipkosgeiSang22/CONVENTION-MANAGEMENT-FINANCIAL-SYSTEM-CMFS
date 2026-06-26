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
    SCOPE_CHOICES = [
        ('county', 'County'),
        ('regional', 'Regional'),
        ('national', 'National'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('financially_closed', 'Financially Closed'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, default='')
    fee_student = models.DecimalField(max_digits=10, decimal_places=2)
    fee_kessat = models.DecimalField(max_digits=10, decimal_places=2)
    fee_associate = models.DecimalField(max_digits=10, decimal_places=2)
    is_registration_open = models.BooleanField(default=False)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft')
    scope_locked = models.BooleanField(default=False)
    created_by_id = models.IntegerField(null=True, blank=True)  # user id from JWT
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conventions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.scope})"


class ConventionUnit(models.Model):
    SCOPE_TYPE_CHOICES = [
        ('county', 'County'),
        ('regional', 'Regional'),
        ('national', 'National'),
    ]

    convention = models.ForeignKey(Convention, on_delete=models.PROTECT, related_name='units')
    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPE_CHOICES)
    scope_id = models.IntegerField(null=True, blank=True)  # counties.id / regions.id / NULL for national
    head_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'convention_units'

    def __str__(self):
        return f"Unit {self.id} — {self.convention.name} ({self.scope_type})"