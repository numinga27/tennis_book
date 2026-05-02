# payment/admin.py
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'user', 'amount', 'payment_method', 'status')
    list_filter = ('status', 'payment_method')
    search_fields = ('booking__court__name', 'user__username')