import secrets
import string

from decouple import config
from django.core.management.base import BaseCommand, CommandError

from auth_app.models import User
from auth_app.utils import hash_password


def _generate_strong_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = (
        'Create the initial Super Admin user. Reads credentials from the '
        'SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD environment variables — '
        'never hardcode real credentials here, this file is committed to '
        'source control. If SUPER_ADMIN_PASSWORD is unset, a random strong '
        'password is generated and printed once (not stored anywhere).'
    )

    def handle(self, *args, **options):
        email = config('SUPER_ADMIN_EMAIL', default='')
        if not email:
            raise CommandError(
                'SUPER_ADMIN_EMAIL is not set. Set it as an environment '
                'variable before running this command — do not hardcode it.'
            )

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Super Admin {email} already exists.'))
            return

        password = config('SUPER_ADMIN_PASSWORD', default='')
        generated = False
        if not password:
            password = _generate_strong_password()
            generated = True

        user = User.objects.create(
            full_name='Super Admin',
            email=email,
            phone='',
            role='super_admin',
            password_hash=hash_password(password),
            totp_enabled=False,
            totp_secret='',
            token_version=1,
            failed_login_attempts=0,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Super Admin created.\n'
            f'  Email:    {email}\n'
            + (f'  Password: {password}  (generated — save this now, it will not be shown again)\n' if generated else '  Password: (the one you set in SUPER_ADMIN_PASSWORD)\n')
            + f'  ID:       {user.id}\n'
            f'  TOTP is disabled — log in once, then immediately enable it via\n'
            f'  /api/auth/totp/setup/ + /api/auth/totp/confirm/ before doing anything else.'
        ))