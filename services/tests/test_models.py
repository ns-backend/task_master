from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from services.models import Booking, Category, Service, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def provider():
    return User.objects.create_user(
        username="model_provider",
        password="password123",
        is_provider=True,
    )


@pytest.fixture
def category():
    return Category.objects.create(
        name="Model tests",
        slug="model-tests",
    )


def test_booking_uses_pending_status_by_default(provider, category):
    client = User.objects.create_user(
        username="model_client",
        password="password123",
    )
    service = Service.objects.create(
        name="Test service",
        description="Test description",
        price=Decimal("100.00"),
        category=category,
        provider=provider,
    )

    booking = Booking.objects.create(
        client=client,
        service=service,
        booking_date=timezone.now() + timezone.timedelta(days=1),
    )

    assert booking.status == Booking.Status.PENDING


@pytest.mark.parametrize(
    ("status_value", "expected_label"),
    [
        (Booking.Status.PENDING, "В ожидании"),
        (Booking.Status.CONFIRMED, "Подтверждено"),
        (Booking.Status.COMPLETED, "Завершено"),
        (Booking.Status.CANCELED, "Отменено"),
    ],
)
def test_booking_status_labels(status_value, expected_label):
    assert status_value.label == expected_label


@pytest.mark.parametrize(
    "invalid_price",
    [
        Decimal("0.00"),
        Decimal("-1.00"),
    ],
)
def test_service_full_clean_rejects_non_positive_price(
    provider,
    category,
    invalid_price,
):
    service = Service(
        name="Invalid service",
        description="Invalid price",
        price=invalid_price,
        category=category,
        provider=provider,
    )

    with pytest.raises(ValidationError):
        service.full_clean()


@pytest.mark.parametrize(
    "invalid_price",
    [
        Decimal("0.00"),
        Decimal("-1.00"),
    ],
)
def test_database_rejects_non_positive_service_price(
    provider,
    category,
    invalid_price,
):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Service.objects.create(
                name="Invalid service",
                description="Invalid price",
                price=invalid_price,
                category=category,
                provider=provider,
            )
