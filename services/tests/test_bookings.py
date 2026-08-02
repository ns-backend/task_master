from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from services.models import Booking


pytestmark = pytest.mark.django_db


def test_client_can_create_booking(
    api_client,
    client_user,
    service,
    future_booking_date,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        '/api/bookings/',
        {
            'service': service.id,
            'booking_date': future_booking_date.isoformat(),
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    booking = Booking.objects.get()

    assert booking.client == client_user
    assert booking.service == service


def test_booking_cannot_be_created_in_past(
    api_client,
    client_user,
    service,
):
    past_date = timezone.now() - timedelta(days=1)

    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        '/api/bookings/',
        {
            'service': service.id,
            'booking_date': past_date.isoformat(),
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Booking.objects.count() == 0


def test_provider_cannot_create_booking(
    api_client,
    provider_user,
    another_service,
    future_booking_date,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        '/api/bookings/',
        {
            'service': another_service.id,
            'booking_date': future_booking_date.isoformat(),
        },
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Booking.objects.count() == 0


def test_booking_cannot_be_updated_with_patch(
    api_client,
    client_user,
    booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        f'/api/bookings/{booking.id}/',
        {
            'status': 'completed',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    booking.refresh_from_db()

    assert booking.status != 'completed'


def test_booking_cannot_be_deleted(
    api_client,
    client_user,
    booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.delete(
        f'/api/bookings/{booking.id}/',
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Booking.objects.filter(id=booking.id).exists()