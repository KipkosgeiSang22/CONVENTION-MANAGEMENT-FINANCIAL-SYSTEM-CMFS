"""
FILE: cmfs/cmfs_backend/reports/dashboard_urls.py
ACTION: CREATE (Phase 11)
"""

from django.urls import path
from .dashboard_views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
