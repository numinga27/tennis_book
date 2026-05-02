# payment/models.py
from django.db import models
from django.conf import settings
from booking.models import Booking

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('card_transfer', 'Перевод на карту'),
        ('online', 'Онлайн оплата'),
        ('cash', 'Наличные'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('completed', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
        ('refunded', 'Возвращено'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, verbose_name='Бронирование')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма (₽)')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name='Способ оплаты')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    transaction_id = models.CharField(max_length=100, verbose_name='ID транзакции', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Оплата'
        verbose_name_plural = 'Оплаты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Оплата #{self.id} - {self.amount} ₽"