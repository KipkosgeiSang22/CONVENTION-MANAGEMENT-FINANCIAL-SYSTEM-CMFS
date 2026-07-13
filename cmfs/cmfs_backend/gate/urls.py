"""
FILE: cmfs/cmfs_backend/gate/urls.py
ACTION: CREATE (Phase 8)

Mounted at /api/gate/ — see cmfs_backend/api_urls.py.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('<int:unit_id>/delegates/', views.GateDelegatesListView.as_view(), name='gate-delegates-list'),
    path('checkin/', views.GateCheckinView.as_view(), name='gate-checkin'),
    path('checkin/batch/', views.GateCheckinBatchView.as_view(), name='gate-checkin-batch'),
    path('checkin/cash-payment/', views.GateCashPaymentCheckinView.as_view(), name='gate-cash-payment-checkin'),
]
