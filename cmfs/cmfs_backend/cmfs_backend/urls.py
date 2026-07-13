from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('cmfs_backend.api_urls')),
]

# Serves /media/qr_codes/..., /media/reports/... etc. This is an acceptable
# stopgap for a moderate-traffic deployment without external object storage
# (S3, Cloudinary, etc.) configured. It requires MEDIA_ROOT to sit on a
# persistent disk in production — Render's default filesystem is ephemeral
# and wipes on every deploy/restart, which would silently delete every
# generated QR code and report between deploys otherwise.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
