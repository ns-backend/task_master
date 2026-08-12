from django.utils import timezone
from rest_framework import serializers

from .models import Booking, Category, Service, User


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_provider",
            "phone_number",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "is_provider",
            "phone_number",
        ]


class ProviderPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "is_provider",
            "phone_number",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "phone_number",
        ]

    def validate(self, attrs):
        allowed_fields = set(self.fields)
        received_fields = set(self.initial_data)

        unknown_fields = received_fields - allowed_fields

        if unknown_fields:
            raise serializers.ValidationError(
                {field: "Это поле нельзя изменять." for field in unknown_fields}
            )

        return attrs


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ServiceWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и редактирования услуг."""

    class Meta:
        model = Service
        fields = ["id", "name", "description", "price", "category"]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля.")
        return value


class ServiceReadSerializer(serializers.ModelSerializer):
    """Сериализатор для подробного отображения услуг."""

    category = CategorySerializer(read_only=True)
    provider = ProviderPublicSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "price",
            "provider",
            "category",
            "created_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с бронированиями."""

    client = serializers.ReadOnlyField(source="client.username")

    class Meta:
        model = Booking
        fields = ["id", "client", "service", "booking_date", "status", "created_at"]
        read_only_fields = [
            "status",
            "client",
        ]  # Статус меняется только через отдельные действия

    def validate_booking_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Дата бронирования должна быть в будущем."
            )

        return value

    def validate(self, attrs):
        request = self.context.get("request")
        service = attrs.get("service")
        booking_date = attrs.get("booking_date")

        if request is None:
            return attrs

        user = request.user

        if service and service.provider_id == user.id:
            raise serializers.ValidationError(
                "Нельзя забронировать собственную услугу."
            )

        if user.is_provider:
            raise serializers.ValidationError(
                "Провайдер не может создавать бронирования."
            )

        if service and booking_date:
            booking_exists = Booking.objects.filter(
                service=service,
                booking_date=booking_date,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            ).exists()

            if booking_exists:
                raise serializers.ValidationError(
                    {"booking_date": ("Это время уже занято для выбранной услуги.")}
                )

        return attrs
