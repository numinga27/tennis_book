# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=20, verbose_name='Телефон', blank=True)
    address = models.TextField(verbose_name='Адрес', blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"