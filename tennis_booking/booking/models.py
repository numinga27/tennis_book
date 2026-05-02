# booking/models.py
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Court(models.Model):
    COURT_TYPES = [
        ('hard', 'Хард'),
        ('clay', 'Грунт'),
        ('grass', 'Трава'),
    ]

    COURT_LOCATION = [
        ('indoor', 'Крытый'),
        ('outdoor', 'Уличный'),
    ]

    number = models.IntegerField(verbose_name='Номер корта', unique=True)
    name = models.CharField(max_length=100, verbose_name='Название корта')
    court_type = models.CharField(
        max_length=20, choices=COURT_TYPES, verbose_name='Тип покрытия')
    location = models.CharField(
        max_length=20, choices=COURT_LOCATION, verbose_name='Расположение')
    price_weekday = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Цена в будни (₽/час)')
    price_weekend = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Цена в выходные (₽/час)')
    description = models.TextField(verbose_name='Описание', blank=True)
    is_active = models.BooleanField(
        default=True, verbose_name='Работает (сезон)')
    is_indoor = models.BooleanField(default=False, verbose_name='Крытый')

    class Meta:
        verbose_name = 'Корт'
        verbose_name_plural = 'Корты'
        ordering = ['number']

    def __str__(self):
        return f"Корт {self.number} - {self.name}"

    def save(self, *args, **kwargs):
        # Автоматически определяем крытый/уличный по location
        self.is_indoor = self.location == 'indoor'
        super().save(*args, **kwargs)

    def get_price_for_date(self, date):
        """Получить цену для конкретной даты"""
        # 0 = Monday, 5 = Saturday, 6 = Sunday
        if date.weekday() >= 5:  # Выходные (суббота, воскресенье)
            return self.price_weekend
        else:  # Будни
            return self.price_weekday


# booking/models.py - обновим модель Booking


class Booking(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('cancelled', 'Отменено'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('card_transfer', 'Перевод на карту'),
        ('online', 'Онлайн оплата'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    court = models.ForeignKey(
        Court, on_delete=models.CASCADE, verbose_name='Корт')
    date = models.DateField(verbose_name='Дата')
    start_time = models.TimeField(verbose_name='Время начала')
    duration = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name='Длительность (часов)', default=Decimal('1.0'))
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Общая стоимость (₽)')
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='Статус оплаты')
    payment_method = models.CharField(
        max_length=50, choices=PAYMENT_METHOD_CHOICES, default='card_transfer', verbose_name='Способ оплаты')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    notes = models.TextField(verbose_name='Примечания', blank=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"Бронь #{self.id} - Корт {self.court.number} - {self.date} {self.start_time}"

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем стоимость при сохранении
        if not self.total_price and self.court and self.duration:
            # Определяем будний или выходной день
            is_weekend = self.date.weekday() >= 5
            price_per_hour = self.court.price_weekend if is_weekend else self.court.price_weekday
            self.total_price = price_per_hour * self.duration
        super().save(*args, **kwargs)


class TimeSlot(models.Model):
    court = models.ForeignKey(
        Court, on_delete=models.CASCADE, verbose_name='Корт')
    date = models.DateField(verbose_name='Дата')
    start_time = models.TimeField(verbose_name='Время начала')
    is_available = models.BooleanField(default=True, verbose_name='Доступен')

    class Meta:
        verbose_name = 'Временной слот'
        verbose_name_plural = 'Временные слоты'
        unique_together = ['court', 'date', 'start_time']

    def __str__(self):
        return f"Корт {self.court.number} - {self.date} {self.start_time}"
