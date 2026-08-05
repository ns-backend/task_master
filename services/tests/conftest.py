from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from services.models import Booking, Category, Service, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="client",
        email="client@example.com",
        password="strong-password-123",
        is_provider=False,
        phone_number="+49111111111",
    )


@pytest.fixture
def provider_user(db):
    return User.objects.create_user(
        username="provider",
        email="provider@example.com",
        password="strong-password-123",
        is_provider=True,
        phone_number="+49222222222",
    )


@pytest.fixture
def another_provider(db):
    return User.objects.create_user(
        username="another_provider",
        email="another-provider@example.com",
        password="strong-password-123",
        is_provider=True,
        phone_number="+49333333333",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="strong-password-123",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(
        name="Ремонт",
        slug="repair",
    )


@pytest.fixture
def service(db, provider_user, category):
    return Service.objects.create(
        name="Сборка мебели",
        description="Сборка шкафов, столов и другой мебели",
        price=Decimal("100.00"),
        provider=provider_user,
        category=category,
    )


@pytest.fixture
def another_service(db, another_provider, category):
    return Service.objects.create(
        name="Установка техники",
        description="Установка домашней техники",
        price=Decimal("100.00"),
        provider=another_provider,
        category=category,
    )


@pytest.fixture
def future_booking_date():
    return timezone.now() + timedelta(days=7)


@pytest.fixture
def booking(db, client_user, service, future_booking_date):
    return Booking.objects.create(
        client=client_user,
        service=service,
        booking_date=future_booking_date,
    )


@pytest.fixture
def another_client(db):
    return User.objects.create_user(
        username="another_client",
        email="another-client@example.com",
        password="strong-password-123",
        is_provider=False,
        phone_number="+49666666666",
    )


@pytest.fixture
def another_client_booking(
    db,
    another_client,
    service,
    future_booking_date,
):
    return Booking.objects.create(
        client=another_client,
        service=service,
        booking_date=future_booking_date,
    )


@pytest.fixture
def another_provider_booking(
    db,
    client_user,
    another_service,
    future_booking_date,
):
    return Booking.objects.create(
        client=client_user,
        service=another_service,
        booking_date=future_booking_date,
    )
