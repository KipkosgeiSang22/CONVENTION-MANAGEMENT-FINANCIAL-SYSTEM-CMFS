from django.urls import path, include
from .views import HealthCheckView
from auth_app.views import InviteUserView, InvalidateSessionsView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('auth/', include('auth_app.urls')),
    path('users/invite/', InviteUserView.as_view(), name='user-invite'),
    path('users/<int:user_id>/invalidate-sessions/', InvalidateSessionsView.as_view(), name='invalidate-sessions'),
]