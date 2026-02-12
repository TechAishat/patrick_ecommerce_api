import os
import django
from django.core.mail import send_mail

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerceApiProject.settings')
django.setup()

def send_test_email():
    try:
        send_mail(
            'Test from Mailtrap API',
            'This is a test email sent via Mailtrap API',
            'noreply@cavanni.com',
            ['aaishat122@gmail.com'],
            fail_silently=False,
        )
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_test_email()