from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


class User(AbstractUser):
    is_provider = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Используем settings.AUTH_USER_MODEL
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.price <= 0:
            raise ValidationError("Цена должна быть больше нуля.")

    def __str__(self):
        return self.name


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('confirmed', 'Подтверждено'),
        ('completed', 'Завершено'),
        ('canceled', 'Отменено'), # Добавил статус отмены
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True) # Дата создания заявки

    def clean(self):
        # Проверка: дата не в прошлом
        if self.booking_date < timezone.now():
            raise ValidationError("Нельзя забронировать на прошедшую дату.")
        # Проверка: клиент не является исполнителем этой услуги
        if self.client == self.service.provider:
            raise ValidationError("Вы не можете забронировать собственную услугу.")

    def __str__(self):
        return f"{self.client.username} -> {self.service.name}"
