# Create apiApp/services.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Notification, EmailNotificationPreference

class NotificationService:
    
    @staticmethod
    def send_notification(user, title, message, notification_type='general', product=None):
        # Create in-app notification
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message
        )
        
        # Check user's email preferences
        try:
            preferences = EmailNotificationPreference.objects.get(user=user)
            
            # Send email if user has this preference enabled
            if getattr(preferences, notification_type, True):
                NotificationService.send_email_notification(
                    user, title, message, product
                )
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.save()
                
        except EmailNotificationPreference.DoesNotExist:
            # Create default preferences and send email
            EmailNotificationPreference.objects.create(user=user)
            NotificationService.send_email_notification(
                user, title, message, product
            )
    
    @staticmethod
    def send_email_notification(user, title, message, product=None):
        subject = f"Your Store - {title}"
        
        # Simple HTML message
        html_message = f"""
        <html>
        <body>
            <h2>Hi {user.full_name or user.email},</h2>
            <p>{message}</p>
            {f'<p>Product: {product.name}</p>' if product else ''}
            <p>Best regards,<br>Your Store Team</p>
        </body>
        </html>
        """
        
        send_mail(
            subject=subject,
            message=message,  # Plain text version
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yourstore.com'),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )