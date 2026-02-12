from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.models import EmailAddress
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Save user, populate full_name from Google data, and handle email verification
        """
        # First, save the user with the parent class
        user = super().save_user(request, sociallogin, form=form)
        
        # Get full name from Google
        extra_data = sociallogin.account.extra_data
        if 'name' in extra_data:
            user.full_name = extra_data['name']
            user.save(update_fields=['full_name'])
        
        # Handle email verification
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0]
            if not email.verified:
                # Send verification email
                email.send_confirmation(request)
                # Store email in session for the email verification sent view
                request.session['account_email_verification_sent'] = email.email
        
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Handle pre-login checks, including email verification
        """
        # Skip if user is already authenticated
        if sociallogin.is_existing:
            return

        # Check if email is verified
        email = sociallogin.email_addresses[0] if sociallogin.email_addresses else None
        if email and not email.verified:
            # Send verification email if not already sent
            if not request.session.get('account_email_verification_sent') == email.email:
                email.send_confirmation(request)
                request.session['account_email_verification_sent'] = email.email
            
            # Redirect to email verification sent page
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('account_email_verification_sent'))

    def authentication_error(self, request, provider_id, error=None, exception=None, **kwargs):
        """
        Handle authentication errors
        """
        messages.error(request, f"Authentication error: {error}")
        return super().authentication_error(request, provider_id, error, exception, **kwargs)