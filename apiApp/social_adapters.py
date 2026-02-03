from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Save user and populate full_name from Google data
        """
        user = super().save_user(request, sociallogin, form=form)
        
        # Get full name from Google
        extra_data = sociallogin.account.extra_data
        if 'name' in extra_data:
            user.full_name = extra_data['name']
            user.save()
        
        return user