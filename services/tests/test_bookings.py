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
        "/api/bookings/",
        {
            "service": service.id,
            "booking_date": future_booking_date.isoformat(),
        },
        format="json",
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
        "/api/bookings/",
        {
            "service": service.id,
            "booking_date": past_date.isoformat(),
        },
        format="json",
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
        "/api/bookings/",
        {
            "service": another_service.id,
            "booking_date": future_booking_date.isoformat(),
        },
        format="json",
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
        f"/api/bookings/{booking.id}/",
        {
            "status": "completed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    booking.refresh_from_db()

    assert booking.status != "completed"


def test_booking_cannot_be_deleted(
    api_client,
    client_user,
    booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.delete(
        f"/api/bookings/{booking.id}/",
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Booking.objects.filter(id=booking.id).exists()


def get_response_results(response):
    if isinstance(response.data, dict) and "results" in response.data:
        return response.data["results"]

    return response.data


def test_client_sees_only_own_bookings(
    api_client,
    client_user,
    booking,
    another_client_booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.get("/api/bookings/")

    assert response.status_code == status.HTTP_200_OK

    results = get_response_results(response)
    booking_ids = {item["id"] for item in results}

    assert booking.id in booking_ids
    assert another_client_booking.id not in booking_ids


def test_provider_sees_only_bookings_for_own_services(
    api_client,
    provider_user,
    booking,
    another_provider_booking,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.get("/api/bookings/")

    assert response.status_code == status.HTTP_200_OK

    results = get_response_results(response)
    booking_ids = {item["id"] for item in results}

    assert booking.id in booking_ids
    assert another_provider_booking.id not in booking_ids


def test_client_cannot_retrieve_another_client_booking(
    api_client,
    client_user,
    another_client_booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.get(
        f"/api/bookings/{another_client_booking.id}/",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_provider_cannot_retrieve_booking_for_another_provider(
    api_client,
    another_provider,
    booking,
):
    api_client.force_authenticate(user=another_provider)

    response = api_client.get(
        f"/api/bookings/{booking.id}/",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_provider_can_confirm_pending_booking(
    api_client,
    provider_user,
    booking,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.status == "confirmed"
    assert response.data["status"] == "confirmed"


def test_client_cannot_confirm_booking(
    api_client,
    client_user,
    booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    booking.refresh_from_db()

    assert booking.status == "pending"


def test_other_provider_cannot_confirm_booking(
    api_client,
    another_provider,
    booking,
):
    api_client.force_authenticate(user=another_provider)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    booking.refresh_from_db()

    assert booking.status == "pending"


def test_confirmed_booking_cannot_be_confirmed_again(
    api_client,
    provider_user,
    booking,
):
    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "confirmed"


def test_provider_can_complete_confirmed_booking(
    api_client,
    provider_user,
    booking,
):
    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/complete/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.status == "completed"
    assert response.data["status"] == "completed"


def test_pending_booking_cannot_be_completed(
    api_client,
    provider_user,
    booking,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/complete/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "pending"


def test_client_cannot_complete_booking(
    api_client,
    client_user,
    booking,
):
    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/complete/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    booking.refresh_from_db()

    assert booking.status == "confirmed"


def test_other_provider_cannot_complete_booking(
    api_client,
    another_provider,
    booking,
):
    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=another_provider)

    response = api_client.post(
        f"/api/bookings/{booking.id}/complete/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    booking.refresh_from_db()

    assert booking.status == "confirmed"


def test_client_can_cancel_pending_booking(
    api_client,
    client_user,
    booking,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/cancel/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.status == "canceled"
    assert response.data["status"] == "canceled"


def test_client_can_cancel_confirmed_booking(
    api_client,
    client_user,
    booking,
):
    booking.status = "confirmed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/cancel/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    booking.refresh_from_db()

    assert booking.status == "canceled"


def test_completed_booking_cannot_be_canceled(
    api_client,
    client_user,
    booking,
):
    booking.status = "completed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/cancel/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "completed"


def test_canceled_booking_cannot_be_canceled_again(
    api_client,
    client_user,
    booking,
):
    booking.status = "canceled"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/cancel/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "canceled"


def test_provider_cannot_cancel_booking(
    api_client,
    provider_user,
    booking,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/cancel/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    booking.refresh_from_db()

    assert booking.status == "pending"


def test_canceled_booking_cannot_be_confirmed(
    api_client,
    provider_user,
    booking,
):
    booking.status = "canceled"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "canceled"


def test_completed_booking_cannot_be_confirmed(
    api_client,
    provider_user,
    booking,
):
    booking.status = "completed"
    booking.save(update_fields=["status"])

    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        f"/api/bookings/{booking.id}/confirm/",
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    booking.refresh_from_db()

    assert booking.status == "completed"
