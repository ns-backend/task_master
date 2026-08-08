from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from services.models import Booking


def _get_booking_for_update(
    *,
    queryset: QuerySet,
    booking_id: int,
) -> Booking:
    return get_object_or_404(
        queryset.select_for_update().select_related(
            "client",
            "service__provider",
        ),
        pk=booking_id,
    )


@transaction.atomic
def confirm_booking(
    *,
    queryset: QuerySet,
    booking_id: int,
    actor,
) -> Booking:
    booking = _get_booking_for_update(
        queryset=queryset,
        booking_id=booking_id,
    )

    if booking.service.provider != actor:
        raise PermissionDenied(
            "Подтвердить бронирование может только провайдер услуги."
        )

    if booking.status != Booking.Status.PENDING:
        raise ValidationError("Подтвердить можно только ожидающее бронирование.")

    booking.status = Booking.Status.CONFIRMED
    booking.save(update_fields=["status"])

    return booking


@transaction.atomic
def complete_booking(
    *,
    queryset: QuerySet,
    booking_id: int,
    actor,
) -> Booking:
    booking = _get_booking_for_update(
        queryset=queryset,
        booking_id=booking_id,
    )

    if booking.service.provider != actor:
        raise PermissionDenied("Завершить бронирование может только провайдер услуги.")

    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError("Завершить можно только подтверждённое бронирование.")

    booking.status = Booking.Status.COMPLETED
    booking.save(update_fields=["status"])

    return booking


@transaction.atomic
def cancel_booking(
    *,
    queryset: QuerySet,
    booking_id: int,
    actor,
) -> Booking:
    booking = _get_booking_for_update(
        queryset=queryset,
        booking_id=booking_id,
    )

    if booking.client != actor:
        raise PermissionDenied("Отменить бронирование может только клиент.")

    allowed_statuses = {
        Booking.Status.PENDING,
        Booking.Status.CONFIRMED,
    }

    if booking.status not in allowed_statuses:
        raise ValidationError("Это бронирование уже нельзя отменить.")

    booking.status = Booking.Status.CANCELED
    booking.save(update_fields=["status"])

    return booking
