"""
Django Admin configuration for auth_app.

Key behaviour:
  - User scope is set directly via county / region fields. Convention-unit
    assignment happens separately, via convention creation.
  - password_hash is intentionally excluded from the form — passwords are set
    via the account-setup flow (/auth/setup/) or via the password-reset flow.
    To create a user here, leave password_hash blank; the user will set it via
    their invite link.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone as dj_tz

from auth_app.models import User, RecoveryCode
from auth_app.utils import generate_setup_token
from django.conf import settings


# ── Inline: Recovery Codes ─────────────────────────────────────────────────────

class RecoveryCodeInline(admin.TabularInline):
    model = RecoveryCode
    extra = 0
    readonly_fields = ['code_hash', 'used', 'used_at', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ── User Admin ─────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # ── List view ──────────────────────────────────────────────────────────────
    list_display = [
        'full_name', 'email', 'role_badge',
        'county', 'region', 'status_badge', 'last_login_at',
    ]
    list_filter = ['role', 'county', 'region', 'totp_enabled']
    search_fields = ['full_name', 'email', 'phone']
    ordering = ['full_name']
    list_per_page = 50

    # ── Detail form ────────────────────────────────────────────────────────────
    fieldsets = [
        ('Identity', {
            'fields': ['full_name', 'email', 'phone', 'role'],
        }),
        ('Scope Assignment', {
            'fields': ['county', 'region'],
            'description': (
                'For Super Admin and National Head, leave County and Region blank.'
            ),
        }),
        ('Security', {
            'fields': ['totp_enabled', 'token_version', 'failed_login_attempts', 'locked_until'],
            'classes': ['collapse'],
        }),
        ('Setup / Reset Token', {
            'fields': ['setup_token', 'setup_token_expires_at'],
            'description': (
                'To manually trigger a new setup invite, click "Regenerate Setup Token" below. '
                'Copy the token and give the URL to the user: '
                f'{settings.FRONTEND_URL}/auth/setup?token=<token>'
            ),
            'classes': ['collapse'],
        }),
        ('Audit', {
            'fields': ['last_login_at', 'last_login_ip', 'created_at'],
            'classes': ['collapse'],
        }),
    ]

    readonly_fields = ['last_login_at', 'last_login_ip', 'created_at', 'token_version']

    inlines = [RecoveryCodeInline]

    # Custom actions
    actions = ['regenerate_setup_token', 'unlock_account', 'invalidate_sessions']

    # ── Computed display columns ───────────────────────────────────────────────

    @admin.display(description='Role')
    def role_badge(self, obj):
        colours = {
            'super_admin':    '#6d28d9',
            'national_head':  '#1d4ed8',
            'regional_head':  '#0369a1',
            'county_head':    '#0e7490',
            'budget_creator': '#15803d',
            'finance_viewer': '#4d7c0f',
            'gate_official':  '#b45309',
            'delegate':       '#6b7280',
        }
        colour = colours.get(obj.role, '#374151')
        label = obj.get_role_display()
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px">{}</span>',
            colour, label,
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj.locked_until and obj.locked_until > dj_tz.now():
            return format_html('<span style="color:#dc2626;font-weight:bold">🔒 Locked</span>')
        if obj.setup_token and not obj.password_hash:
            return format_html('<span style="color:#d97706">⏳ Pending Setup</span>')
        if not obj.totp_enabled:
            return format_html('<span style="color:#f59e0b">⚠ No TOTP</span>')
        return format_html('<span style="color:#16a34a">✓ Active</span>')

    # ── Admin actions ──────────────────────────────────────────────────────────

    @admin.action(description='Regenerate setup token (48-hour invite link)')
    def regenerate_setup_token(self, request, queryset):
        """
        Generates a fresh 48-hour setup token for each selected user and
        prints the setup URLs to the Django message area.
        Use this when email delivery is unavailable — copy the URL and send
        it to the user directly.
        """
        from datetime import timedelta
        messages_out = []
        for user in queryset:
            token = generate_setup_token()
            user.setup_token = token
            user.setup_token_expires_at = dj_tz.now() + timedelta(hours=48)
            user.password_hash = ''   # force re-setup
            user.totp_enabled = False
            user.totp_secret = ''
            user.save(update_fields=[
                'setup_token', 'setup_token_expires_at',
                'password_hash', 'totp_enabled', 'totp_secret',
            ])
            RecoveryCode.objects.filter(user=user).delete()
            url = f"{settings.FRONTEND_URL}/auth/setup?token={token}"
            messages_out.append(f"{user.full_name} ({user.email}): {url}")

        self.message_user(
            request,
            format_html(
                'Setup links generated. Send these URLs to users directly:<br/>'
                + '<br/>'.join(f'<code>{m}</code>' for m in messages_out)
            ),
        )

    @admin.action(description='Unlock account (clear login lockout)')
    def unlock_account(self, request, queryset):
        queryset.update(locked_until=None, failed_login_attempts=0)
        self.message_user(request, f'{queryset.count()} account(s) unlocked.')

    @admin.action(description='Invalidate all sessions (force re-login)')
    def invalidate_sessions(self, request, queryset):
        for user in queryset:
            user.token_version += 1
            user.save(update_fields=['token_version'])
        self.message_user(request, f'{queryset.count()} user(s) sessions invalidated.')


# ── Recovery Code Admin (read-only audit view) ─────────────────────────────────

@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'used', 'used_at', 'created_at']
    list_filter = ['used']
    search_fields = ['user__full_name', 'user__email']
    readonly_fields = ['user', 'code_hash', 'used', 'used_at', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False