import sys
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Test SMTP email delivery to verify if Gmail credentials are working."

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default=getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            help='Recipient email address to send test message to.',
        )

    def handle(self, *args, **options):
        recipient = options['to'] or getattr(settings, 'EMAIL_HOST_USER', '')
        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', ''))
        user = getattr(settings, 'EMAIL_HOST_USER', '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')

        masked_pw = (password[:3] + '*' * 8 + password[-2:]) if len(password) >= 6 else '***'

        self.stdout.write(f"\n--- Testing SMTP Configuration ---")
        self.stdout.write(f"EMAIL_HOST:          {getattr(settings, 'EMAIL_HOST', '')}")
        self.stdout.write(f"EMAIL_PORT:          {getattr(settings, 'EMAIL_PORT', '')}")
        self.stdout.write(f"EMAIL_USE_TLS:       {getattr(settings, 'EMAIL_USE_TLS', '')}")
        self.stdout.write(f"EMAIL_HOST_USER:      {user}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD:  {masked_pw} (length: {len(password)})")
        self.stdout.write(f"Sending test email to: {recipient} ...\n")

        try:
            result = send_mail(
                subject="KOPPEE - SMTP Test Email",
                message=(
                    "Congratulations!\n\n"
                    "Your KOPPEE Django email configuration is working perfectly.\n"
                    "Registration OTPs and reservation notifications will now be delivered to customer inboxes."
                ),
                from_email=sender,
                recipient_list=[recipient],
                fail_silently=False,
            )
            if result:
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Email successfully delivered to {recipient}!"))
            else:
                self.stdout.write(self.style.WARNING(f"[WARNING] send_mail returned 0 (no email sent)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAILED] Could not send email via SMTP:"))
            self.stdout.write(self.style.ERROR(f"         Error: {type(e).__name__}: {e}\n"))

            if "535" in str(e) or "BadCredentials" in str(e) or "Username and Password not accepted" in str(e):
                self.stdout.write(self.style.WARNING(
                    "--> GOOGLE SMTP DIAGNOSIS:\n"
                    "    Google rejected your username/password (BadCredentials).\n"
                    "    To fix:\n"
                    "    1. Open https://myaccount.google.com/apppasswords in your browser.\n"
                    f"    2. Ensure you are signed in as: {user}\n"
                    "    3. Under 'App name', type 'Django' and click 'Create'.\n"
                    "    4. Copy the new 16-character password.\n"
                    "    5. Paste it in shop/.env as EMAIL_HOST_PASSWORD=your_new_password\n"
                    "    6. Run this command again: python manage.py test_email\n"
                ))
