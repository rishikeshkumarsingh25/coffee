"""
URL configuration for shop project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Custom Admin Branding
admin.site.site_header = "KOPPEE Administration"
admin.site.site_title = "KOPPEE Admin Portal"
admin.site.index_title = "Welcome to KOPPEE Management"

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('products.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
