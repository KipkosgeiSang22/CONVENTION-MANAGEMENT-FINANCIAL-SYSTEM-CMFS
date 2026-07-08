"""
FILE: cmfs/cmfs_backend/conventions/urls.py
ACTION: CREATE (Phase 3)
"""

from django.urls import path
from . import views

urlpatterns = [
    # Geography lookups (for wizard dropdowns)
    path('counties/', views.CountyListView.as_view(), name='county-list'),
    path('regions/', views.RegionListView.as_view(), name='region-list'),

    # Convention CRUD
    path('', views.ConventionListCreateView.as_view(), name='convention-list-create'),
    path('<int:pk>/', views.ConventionDetailView.as_view(), name='convention-detail'),

    # Lifecycle transitions
    path('<int:pk>/publish/', views.ConventionPublishView.as_view(), name='convention-publish'),
    path('<int:pk>/activate/', views.ConventionActivateView.as_view(), name='convention-activate'),
    path('<int:pk>/end/', views.ConventionEndView.as_view(), name='convention-end'),
    path('<int:pk>/close/', views.ConventionCloseView.as_view(), name='convention-close'),
    path('<int:pk>/archive/', views.ConventionArchiveView.as_view(), name='convention-archive'),

    # Reports
    path('<int:pk>/opening-day-reports/', views.ConventionOpeningDayReportsView.as_view(), name='convention-opening-reports'),
]
