from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class CustomSignupForm(SignupForm):
    full_name = forms.CharField(
        max_length=255,
        label=_("Full Name"),
        widget=forms.TextInput(attrs={'placeholder': _('Enter your full name')}),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the default username field since we're using email
        if 'username' in self.fields:
            del self.fields['username']
        # Make email required (it should be by default)
        self.fields['email'].required = True

    def save(self, request):
        # Generate verification token
        verification_token = str(uuid.uuid4())
        
        # Save the user with the full name and verification token
        user = super().save(request)
        user.full_name = self.cleaned_data['full_name']
        user.verification_token = verification_token
        user.verification_token_created_at = timezone.now()
        user.is_active = False  # User will be inactive until email is verified
        user.save()
        
        # Send verification email
        self.send_verification_email(request, user, verification_token)
        
        return user

    def send_verification_email(self, request, user, verification_token):
        verification_url = self.get_verification_url(request, verification_token)
        
        subject = _("Verify your email address")
        message = _("""
        Hi {full_name},
        
        Thank you for registering with Patrick Cavanni. 
        Please click the link below to verify your email address:
        
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you did not create an account, please ignore this email.
        
        Best regards,
        The Patrick Cavanni Team
        """).format(
            full_name=user.full_name or user.email,
            verification_url=verification_url
        )
        
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    def get_verification_url(self, request, token):
        path = reverse('verify-email', kwargs={'token': token})
        return request.build_absolute_uri(path)