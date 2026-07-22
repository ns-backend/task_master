from rest_framework import serializers
from .models import User, Category, Service, Booking
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_provider', 'phone_number']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


# Этот для создания и редактирования (принимает ID категории)
class ServiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'category']

    def validate_price(self, value): # Перенесли сюда
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля.")
        return value


# Этот для отображения (показывает детали категории)
class ServiceReadSerializer(serializers.ModelSerializer):
    # Вкладываем сериализатор категории внутрь
    category = CategorySerializer(read_only=True)
    provider = UserSerializer(read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'provider', 'category', 'created_at']


# class ServiceSerializer(serializers.ModelSerializer):
#     # Чтобы в API мы видели имя категории, а не ID
#     category_name = serializers.ReadOnlyField(source='category.name')
#     # Делаем provider только для чтения, будем назначать его в view.py автоматически
#     provider = serializers.ReadOnlyField(source='provider.username')

#     class Meta:
#         model = Service
#         fields = ['id', 'name', 'description', 'price', 'provider', 'category', 'category_name']

#     def validate_price(self, value):
#         if value <= 0:
#             raise serializers.ValidationError("Цена должна быть больше нуля.")
#         return value


class BookingSerializer(serializers.ModelSerializer):
    client = serializers.ReadOnlyField(source='client.username')

    class Meta:
        model = Booking
        fields = ['id', 'client', 'service', 'booking_date', 'status', 'created_at']

    def validate_booking_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Нельзя забронировать на прошлое время.")
        return value
