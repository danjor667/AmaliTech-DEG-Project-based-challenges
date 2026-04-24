from django.urls import path

from .views import TransactionView

urlpatterns = [
    path('process-payment', TransactionView.as_view(), name='process-payment'),
]