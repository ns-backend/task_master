import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from services.booking_services import (
    cancel_booking,
    complete_booking,
    confirm_booking,
)
from services.models import Booking

pytestmark = pytest.mark.django_db


def test_provider_can_confirm_pending_booking(booking, provider_user):
    result = confirm_booking(
        booking=booking,
        actor=provider_user,
    )

    booking.refresh_from_db()

    assert result == booking
    assert booking.status == Booking.Status.CONFIRMED


def test_client_cannot_confirm_booking(booking, client_user):
    with pytest.raises(PermissionDenied):
        confirm_booking(
            booking=booking,
            actor=client_user,
        )


def test_confirm_requires_pending_status(booking, provider_user):
    booking.status = Booking.Status.CANCELED
    booking.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        confirm_booking(
            booking=booking,
            actor=provider_user,
        )


def test_provider_can_complete_confirmed_booking(
    booking,
    provider_user,
):
    booking.status = Booking.Status.CONFIRMED
    booking.save(update_fields=["status"])

    complete_booking(
        booking=booking,
        actor=provider_user,
    )

    booking.refresh_from_db()

    assert booking.status == Booking.Status.COMPLETED


def test_complete_requires_confirmed_status(
    booking,
    provider_user,
):
    with pytest.raises(ValidationError):
        complete_booking(
            booking=booking,
            actor=provider_user,
        )


@pytest.mark.parametrize(
    "initial_status",
    [
        Booking.Status.PENDING,
        Booking.Status.CONFIRMED,
    ],
)
def test_client_can_cancel_active_booking(
    booking,
    client_user,
    initial_status,
):
    booking.status = initial_status
    booking.save(update_fields=["status"])

    cancel_booking(
        booking=booking,
        actor=client_user,
    )

    booking.refresh_from_db()

    assert booking.status == Booking.Status.CANCELED


def test_provider_cannot_cancel_booking(
    booking,
    provider_user,
):
    with pytest.raises(PermissionDenied):
        cancel_booking(
            booking=booking,
            actor=provider_user,
        )


@pytest.mark.parametrize(
    "initial_status",
    [
        Booking.Status.COMPLETED,
        Booking.Status.CANCELED,
    ],
)
def test_client_cannot_cancel_inactive_booking(
    booking,
    client_user,
    initial_status,
):
    booking.status = initial_status
    booking.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        cancel_booking(
            booking=booking,
            actor=client_user,
        )
