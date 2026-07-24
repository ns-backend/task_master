from django.utils import timezone
from rest_framework import serializers

from .models import User, Category, Service, Booking


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_provider', 'phone_number']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ServiceWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования услуг."""
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'category']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля.")
        return value


class ServiceReadSerializer(serializers.ModelSerializer):
    """Сериализатор для подробного отображения услуг."""
    category = CategorySerializer(read_only=True)
    provider = UserSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'price', 
            'provider', 'category', 'created_at'
        ]


class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с бронированиями."""
    client = serializers.ReadOnlyField(source='client.username')

    class Meta:
        model = Booking
        fields = [
            'id', 'client', 'service', 'booking_date', 
            'status', 'created_at'
        ]
        read_only_fields = ['status'] # Статус меняется только через отдельные действия

    def validate_booking_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Нельзя забронировать на прошлое время.")
        return value