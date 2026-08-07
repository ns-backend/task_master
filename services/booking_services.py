from rest_framework.exceptions import PermissionDenied, ValidationError

from services.models import Booking


def confirm_booking(*, booking: Booking, actor) -> Booking:
    if booking.service.provider != actor:
        raise PermissionDenied(
            "Подтвердить бронирование может только провайдер услуги."
        )

    if booking.status != Booking.Status.PENDING:
        raise ValidationError("Подтвердить можно только ожидающее бронирование.")

    booking.status = Booking.Status.CONFIRMED
    booking.save(update_fields=["status"])

    return booking


def complete_booking(*, booking: Booking, actor) -> Booking:
    if booking.service.provider != actor:
        raise PermissionDenied("Завершить бронирование может только провайдер услуги.")

    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError("Завершить можно только подтверждённое бронирование.")

    booking.status = Booking.Status.COMPLETED
    booking.save(update_fields=["status"])

    return booking


def cancel_booking(*, booking: Booking, actor) -> Booking:
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
