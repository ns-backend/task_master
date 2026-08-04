from django.utils import timezone
from rest_framework import serializers

from .models import User, Category, Service, Booking


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'is_provider',
            'phone_number',
        ]
        read_only_fields = [
            'id',
            'username',
            'email',
            'is_provider',
            'phone_number',
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'is_provider',
            'phone_number',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'phone_number',
        ]


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
    provider = UserReadSerializer(read_only=True)

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
        read_only_fields = ['status', 'client'] # Статус меняется только через отдельные действия

    def validate_booking_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                'Дата бронирования должна быть в будущем.'
            )

        return value

    def validate(self, attrs):
        request = self.context.get('request')
        service = attrs.get('service')

        if request is None:
            return attrs

        user = request.user

        if service and service.provider_id == user.id:
            raise serializers.ValidationError(
                'Нельзя забронировать собственную услугу.'
            )

        if user.is_provider:
            raise serializers.ValidationError(
                'Провайдер не может создавать бронирования.'
            )

        return attrs