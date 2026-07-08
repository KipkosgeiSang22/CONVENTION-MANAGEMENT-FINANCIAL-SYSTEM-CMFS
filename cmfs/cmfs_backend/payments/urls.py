"""
FILE: cmfs/cmfs_backend/payments/urls.py
ACTION: CREATE (Phase 6)
"""

from django.urls import path
from . import views

urlpatterns = [
    path('mpesa/initiate/', views.MpesaInitiateView.as_view(), name='mpesa-initiate'),
    path('mpesa/callback/', views.MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('cash/', views.CashPaymentView.as_view(), name='payment-cash'),
]