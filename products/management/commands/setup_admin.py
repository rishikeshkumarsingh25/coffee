from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create or reset a staff administrator account for KOPPEE Dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            '--username',
            dest='email',
            type=str,
            default='admin',
            help='Admin username or email (any string, valid email NOT required: e.g. admin)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Admin password (default: admin123)',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password']

        user, created = User.objects.get_or_create(email=email)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] {action} administrator account:\n"
                f"     Email / Username: {user.email}\n"
                f"     Password:         {password}\n"
                f"     Admin URL:        /admin-login/\n"
                f"     Dashboard:        /dashboard/"
            )
        )
