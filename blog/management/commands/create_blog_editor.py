from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new blog editor user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address of the blog editor')
        parser.add_argument('--username', type=str, help='Username (defaults to email prefix)')
        parser.add_argument('--first-name', type=str, default='', help='First name')
        parser.add_argument('--last-name', type=str, default='', help='Last name')
        parser.add_argument('--password', type=str, help='Password (will prompt if not provided)')

    def handle(self, *args, **options):
        email = options['email']
        
        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            self.stderr.write(self.style.ERROR('Error: Invalid email address'))
            return

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User with email {email} already exists. Updating to blog editor...'))
            user = User.objects.get(email=email)
            user.user_type = 'blog_editor'
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {email} as blog editor'))
            return

        # Get or generate username
        username = options['username'] or email.split('@')[0]
        
        # Ensure username is unique
        if User.objects.filter(username=username).exists():
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

        # Get password
        password = options['password']
        if not password:
            from getpass import getpass
            while True:
                password = getpass('Enter password: ')
                password_confirm = getpass('Confirm password: ')
                if password == password_confirm:
                    break
                self.stderr.write("Error: Passwords don't match. Please try again.")

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=options['first_name'],
                last_name=options['last_name'],
                user_type='blog_editor'  # Changed from is_blog_editor to user_type
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created blog editor: {email}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error creating user: {str(e)}'))
            raise  # This will show the full traceback for debugging