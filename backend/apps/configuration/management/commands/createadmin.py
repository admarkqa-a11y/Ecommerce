import getpass
import pyotp
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from apps.identity.models import User
from apps.identity.views import cipher

class Command(BaseCommand):
    help='Interactively create the first client Super Admin and a TOTP enrollment URI.'
    def add_arguments(self,parser):parser.add_argument('--email',required=True)
    def handle(self,*args,**options):
        email=options['email'].strip().lower();validate_email(email)
        if User.objects.filter(email=email).exists():raise CommandError('This identity already exists. Use an audited recovery procedure.')
        password=getpass.getpass('New password (12+ characters): ')
        if password!=getpass.getpass('Repeat password: '):raise CommandError('Passwords do not match.')
        validate_password(password)
        secret=pyotp.random_base32()
        user=User.objects.create_superuser(username=email,email=email,password=password,email_verified=True)
        user.mfa_secret=cipher().encrypt(secret.encode()).decode();user.save()
        self.stdout.write('Add this private enrollment URI to your authenticator; do not share it:')
        self.stdout.write(pyotp.TOTP(secret).provisioning_uri(name=email,issuer_name='Retail Admin'))
        self.stdout.write(self.style.SUCCESS('Admin created. Sign in with password and authenticator code.'))

