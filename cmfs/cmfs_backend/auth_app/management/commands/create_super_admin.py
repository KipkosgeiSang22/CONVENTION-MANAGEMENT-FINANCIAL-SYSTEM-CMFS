from django.core.management.base import BaseCommand
from auth_app.models import User
from auth_app.utils import hash_password


class Command(BaseCommand):
    help = 'Create the initial Super Admin user for Phase 2 testing'

    def handle(self, *args, **options):
        email = 'jsang542@gmail.com'

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Super Admin {email} already exists.'))
            return

        user = User.objects.create(
            full_name='Super Admin',
            email=email,
            phone='',
            role='super_admin',
            password_hash=hash_password('Admin@1234'),
            totp_enabled=False,
            totp_secret='',
            token_version=1,
            failed_login_attempts=0,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Super Admin created.\n'
            f'  Email:    {email}\n'
            f'  Password: Admin@1234\n'
            f'  ID:       {user.id}\n'
            f'  Note: TOTP is disabled — this user will log in without TOTP.\n'
            f'  Use /api/auth/totp/setup/ + /api/auth/totp/confirm/ to enable it after first login.'
        ))