# payment/urls.py
from django.urls import path
from . import views

app_name = 'payment'  # Это создает namespace 'payment'

urlpatterns = [
    path('process/<int:booking_id>/', views.process_payment, name='process_payment'),
]