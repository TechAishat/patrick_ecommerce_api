from django.core.management.base import BaseCommand 
from allauth.socialaccount.models import SocialApp 
from django.contrib.sites.models import Site 
 
class Command(BaseCommand): 
    help = 'Fixes Google OAuth configuration' 
 
    def handle(self, *args, **options): 
        try: 
            # Get or create the site 
            site, _ = Site.objects.get_or_create( 
                domain='aishat.pythonanywhere.com', 
                defaults={'name': 'Patrick Cavanni'} 
            ) 
ECHO is off.
            # Delete all Google apps first 
            deleted = SocialApp.objects.filter(provider='google').delete() 
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted[0]} existing Google apps')) 
ECHO is off.
            # Create a fresh one 
            app = SocialApp.objects.create( 
                provider='google', 
                name='Google OAuth', 
                client_id='832940295206-nbp1eeodf3lts7sf8p3dbbta7hsohedm.apps.googleusercontent.com', 
                secret='YOUR_GOOGLE_SECRET'  # Replace with your actual secret 
            ) 
            app.sites.add(site) 
            app.save() 
ECHO is off.
            self.stdout.write(self.style.SUCCESS('Successfully reset Google OAuth app')) 
            self.stdout.write(f"Client ID: {app.client_id}") 
            self.stdout.write(f"Site: {site.domain}") 
            return True 
        except Exception as e: 
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}')) 
            return False 
