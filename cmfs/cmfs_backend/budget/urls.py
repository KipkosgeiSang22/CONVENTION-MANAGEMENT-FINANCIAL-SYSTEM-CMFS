"""
FILE: cmfs/cmfs_backend/budget/urls.py
ACTION: CREATE (Phase 5)

Mounted at /api/units/<unit_id>/budget/... and /api/budget/... — see
cmfs_backend/api_urls.py for exact prefixes.
"""

from django.urls import path
from . import views

# Included at /api/units/<int:unit_id>/budget/
unit_scoped_urlpatterns = [
    path('income/', views.BudgetIncomeView.as_view(), name='budget-income'),
    path('expenses/', views.BudgetExpenseItemsView.as_view(), name='budget-expenses'),
    path('summary/', views.BudgetSummaryView.as_view(), name='budget-summary'),
]

# Included at /api/budget/
urlpatterns = [
    path('expense-items/preloaded/', views.PreloadedExpenseItemListView.as_view(), name='budget-preloaded-items'),
    path('income/<int:pk>/', views.BudgetIncomeDetailView.as_view(), name='budget-income-detail'),
    path('expenses/<int:pk>/', views.BudgetExpenseItemDetailView.as_view(), name='budget-expense-detail'),
]