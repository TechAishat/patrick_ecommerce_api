# apiApp/management/commands/reset_social_apps.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Completely reset social apps and create a fresh Google OAuth app'

    def handle(self, *args, **options):
        try:
            # Delete all social apps and their site associations
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM socialaccount_socialapp_sites;")
                cursor.execute("DELETE FROM socialaccount_socialapp;")
                cursor.execute("DELETE FROM socialaccount_socialtoken;")
                cursor.execute("DELETE FROM socialaccount_socialaccount;")
                self.stdout.write(self.style.SUCCESS('Deleted all social apps and tokens'))

            # Get or create site
            site, created = Site.objects.get_or_create(
                domain='aishat.pythonanywhere.com',
                defaults={'name': 'Patrick Cavanni'}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created new site: {site.domain}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing site: {site.domain}'))

            self.stdout.write(self.style.SUCCESS('Social apps have been completely reset.'))
            self.stdout.write(self.style.SUCCESS('Run the following in the Python shell to create a new Google OAuth app:'))
            self.stdout.write("""
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

site = Site.objects.get(domain='aishat.pythonanywhere.com')
app = SocialApp.objects.create(
    provider='google',
    name='Google OAuth',
    client_id='832940295206-nbp1eeodf3lts7sf8p3dbbta7hsohedm.apps.googleusercontent.com',
    secret='YOUR_GOOGLE_SECRET'  # Replace with your actual secret
)
app.sites.add(site)
app.save()
print(f"Created new Google OAuth app for {site.domain}")
            """)
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))