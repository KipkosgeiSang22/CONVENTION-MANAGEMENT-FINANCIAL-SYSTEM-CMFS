from django.urls import path, include
from .views import HealthCheckView
from .email_preview import EmailPreviewView
from auth_app.views import (
    InviteUserView,
    InvalidateSessionsView,
    UserListView,
    PatchUserView,
    DeleteUserView,
)
from conventions.views import MyUnitsView
from budget.urls import unit_scoped_urlpatterns as budget_unit_urlpatterns
from budget.urls import urlpatterns as budget_urlpatterns
from delegates.urls import unit_scoped_urlpatterns as delegate_unit_urlpatterns

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('auth/', include('auth_app.urls')),

    # User management
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/invite/', InviteUserView.as_view(), name='user-invite'),
    path('users/<int:user_id>/', PatchUserView.as_view(), name='user-patch'),
    path('users/<int:user_id>/delete/', DeleteUserView.as_view(), name='user-delete'),
    path('users/<int:user_id>/invalidate-sessions/', InvalidateSessionsView.as_view(), name='invalidate-sessions'),

    # Resolves the caller's applicable ConventionUnit(s)
    path('my-units/', MyUnitsView.as_view(), name='my-units'),

    # Conventions
    path('conventions/', include('conventions.urls')),

    # Budget (Phase 5)
    path('units/<int:unit_id>/budget/', include(budget_unit_urlpatterns)),
    path('budget/', include(budget_urlpatterns)),

    # Delegates (Phase 6)
    path('units/<int:unit_id>/delegates/', include(delegate_unit_urlpatterns)),
    path('delegates/', include('delegates.urls')),

    # Payments (Phase 6)
    path('payments/', include('payments.urls')),

    # Email preview (Phase 7, DEBUG only)
    path('email-preview/', EmailPreviewView.as_view(), name='email-preview-list'),
    path('email-preview/<str:template_name>/', EmailPreviewView.as_view(), name='email-preview-detail'),
]