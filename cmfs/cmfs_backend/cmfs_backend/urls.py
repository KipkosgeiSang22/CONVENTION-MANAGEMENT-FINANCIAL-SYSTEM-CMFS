from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('cmfs_backend.api_urls')),
]

# Phase 7: serve /media/qr_codes/... locally. In production this should
# be handled by the web server / object storage, not Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)