"""
FILE: cmfs/cmfs_backend/delegates/urls.py
ACTION: CREATE (Phase 6)
"""

from django.urls import path
from . import views
from payments.views import DelegatePaymentsListView

urlpatterns = [
    path('register/options/', views.RegistrationOptionsView.as_view(), name='delegate-register-options'),
    path('register/', views.PublicRegistrationView.as_view(), name='delegate-register'),
    path('registration-status/<int:pk>/', views.RegistrationStatusView.as_view(), name='delegate-registration-status'),
    path('manual/', views.ManualRegistrationView.as_view(), name='delegate-manual-register'),
    path('<str:delegate_id>/payments/', DelegatePaymentsListView.as_view(), name='delegate-payments'),
    path('<str:delegate_id>/', views.DelegateDetailView.as_view(), name='delegate-detail'),
]

# Included at /api/units/<int:unit_id>/delegates/ — see cmfs_backend/api_urls.py
unit_scoped_urlpatterns = [
    path('', views.UnitDelegatesListView.as_view(), name='unit-delegates-list'),
    path('summary/', views.UnitDelegatesSummaryView.as_view(), name='unit-delegates-summary'),
]