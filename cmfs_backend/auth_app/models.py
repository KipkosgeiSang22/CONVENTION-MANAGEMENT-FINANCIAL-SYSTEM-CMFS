from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('national_head', 'National Head'),
        ('regional_head', 'Regional Head'),
        ('county_head', 'County Head'),
        ('budget_creator', 'Budget Creator'),
        ('finance_viewer', 'Finance Viewer'),
        ('gate_official', 'Gate Official'),
        ('delegate', 'Delegate'),
    ]

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    convention_unit = models.ForeignKey(
        'conventions.ConventionUnit',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='users'
    )
    county = models.ForeignKey(
        'conventions.County',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='users'
    )
    region = models.ForeignKey(
        'conventions.Region',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='users'
    )
    password_hash = models.CharField(max_length=255)
    totp_secret = models.CharField(max_length=64, blank=True, default='')
    totp_enabled = models.BooleanField(default=False)
    token_version = models.IntegerField(default=0)
    setup_token = models.CharField(max_length=128, blank=True, default='')
    setup_token_expires_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.full_name} ({self.role})"


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_codes')
    code_hash = models.CharField(max_length=255)  # bcrypt hash — never plain text
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recovery_codes'

    def __str__(self):
        return f"RecoveryCode for user {self.user_id} — used={self.used}"