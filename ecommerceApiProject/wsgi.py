"""
WSGI config for ecommerceApiProject project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# Add your project directory to the Python path
path = '/home/Aishat/patrick_ecommerce_api'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerceApiProject.settings')

# Initialize Django application
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

application = get_wsgi_application()

# Serve media files in production
if os.environ.get('PYTHONANYWHERE_DOMAIN'):
    application = WhiteNoise(application, root=os.path.join(path, 'media'))
    application.add_files(os.path.join(path, 'media'), prefix='media/')