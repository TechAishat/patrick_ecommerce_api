from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm

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
        # Save the user with the full name
        user = super().save(request)
        user.full_name = self.cleaned_data['full_name']
        user.save()
        return user