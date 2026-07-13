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

# Included at /api/units/<int:unit_id>/actuals/ (Phase 9)
actuals_unit_scoped_urlpatterns = [
    path('expenses/', views.ActualExpensesView.as_view(), name='actuals-expenses'),
    path('unbudgeted/', views.UnbudgetedExpenseView.as_view(), name='actuals-unbudgeted'),
    path('summary/', views.ActualsSummaryView.as_view(), name='actuals-summary'),
    path('outstanding/', views.OutstandingPaymentsView.as_view(), name='actuals-outstanding'),
]

# Included at /api/budget/
urlpatterns = [
    path('expense-items/preloaded/', views.PreloadedExpenseItemListView.as_view(), name='budget-preloaded-items'),
    path('income/<int:pk>/', views.BudgetIncomeDetailView.as_view(), name='budget-income-detail'),
    path('income/<int:pk>/actual/', views.BudgetIncomeActualView.as_view(), name='budget-income-actual'),
    path('expenses/<int:pk>/', views.BudgetExpenseItemDetailView.as_view(), name='budget-expense-detail'),
    path('actuals/<int:pk>/', views.ActualExpenseDetailView.as_view(), name='actuals-detail'),
]