# booking/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('courts/', views.courts_list, name='courts_list'),
    path('schedule/', views.schedule, name='schedule'),
    path('book/', views.create_booking, name='create_booking'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:booking_id>/',
         views.cancel_booking, name='cancel_booking'),
    path('confirm-payment/<int:booking_id>/',
         views.confirm_payment, name='confirm_payment'),
]
