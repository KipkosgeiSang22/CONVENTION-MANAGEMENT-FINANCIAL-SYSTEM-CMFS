"""
FILE: cmfs/cmfs_backend/reports/urls.py
ACTION: CREATE (Phase 10)
"""

from django.urls import path
from . import views

urlpatterns = [
    path('convention/<int:convention_id>/', views.ConventionReportsView.as_view(), name='reports-by-convention'),
    path('unit/<int:unit_id>/', views.UnitReportsView.as_view(), name='reports-by-unit'),
    path('<int:report_id>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('<int:report_id>/download/', views.ReportDownloadView.as_view(), name='report-download'),

    # DEV/TESTING CONVENIENCE — see DevGenerateReportsView docstring.
    path('dev-generate/<int:convention_id>/', views.DevGenerateReportsView.as_view(), name='reports-dev-generate'),

    # Annual Summary (Phase 11)
    path('annual-summary/', views.AnnualSummaryListView.as_view(), name='annual-summary-list'),
    path('annual-summary/<int:year>/download/', views.AnnualSummaryDownloadView.as_view(), name='annual-summary-download'),
    path('annual-summary/dev-generate/<int:year>/', views.DevGenerateAnnualSummaryView.as_view(), name='annual-summary-dev-generate'),
]
