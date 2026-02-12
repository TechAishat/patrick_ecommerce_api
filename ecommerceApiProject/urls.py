"""
URL configuration for ecommerceApiProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from blog.admin import blog_admin_site
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic import RedirectView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="Patrick Cavanni API",
        default_version='v1',
        description="API documentation for Patrick Cavanni E-commerce",
        terms_of_service="https://www.patrickcavanni.com/terms/",
        contact=openapi.Contact(email="contact@patrickcavanni.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    path('blog-admin/', blog_admin_site.urls),
    
    # API
    path('api/', include('apiApp.urls')),  # Directly include apiApp.urls
    path('api/token/', obtain_auth_token, name='api_token_auth'),  # Move token endpoint
    
    # Auth
    path('accounts/', include('allauth.urls')),
    
    # Blog
    path('blog/', include('blog.urls')),

    # Add this line to redirect root URL to your main page
    path('', RedirectView.as_view(url='/api/', permanent=False)),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

# This is only needed during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)