from threading import Event, Thread

import pytest
from django.db import close_old_connections, connection, transaction

from services.booking_services import complete_booking
from services.models import Booking, User


@pytest.mark.django_db(transaction=True)
def test_complete_booking_waits_for_concurrent_confirmation(
    booking,
    provider_user,
):
    if connection.vendor != "postgresql":
        pytest.skip("Concurrency test requires PostgreSQL.")

    booking_id = booking.pk
    provider_id = provider_user.pk

    confirmation_ready = Event()
    release_confirmation = Event()
    completion_started = Event()
    completion_finished = Event()

    thread_errors = []
    completion_results = []

    def confirm_in_first_transaction():
        close_old_connections()

        try:
            with transaction.atomic():
                locked_booking = Booking.objects.select_for_update().get(
                    pk=booking_id,
                )

                locked_booking.status = Booking.Status.CONFIRMED
                locked_booking.save(update_fields=["status"])

                confirmation_ready.set()

                if not release_confirmation.wait(timeout=5):
                    raise TimeoutError(
                        "Timed out waiting to release confirmation transaction."
                    )
        except Exception as exc:
            thread_errors.append(exc)
            confirmation_ready.set()
        finally:
            close_old_connections()

    def complete_in_second_transaction():
        close_old_connections()

        try:
            if not confirmation_ready.wait(timeout=5):
                raise TimeoutError("Timed out waiting for confirmation transaction.")

            actor = User.objects.get(pk=provider_id)

            completion_started.set()

            result = complete_booking(
                queryset=Booking.objects.all(),
                booking_id=booking_id,
                actor=actor,
            )

            completion_results.append(result.status)
        except Exception as exc:
            thread_errors.append(exc)
        finally:
            completion_finished.set()
            close_old_connections()

    confirmation_thread = Thread(
        target=confirm_in_first_transaction,
    )
    completion_thread = Thread(
        target=complete_in_second_transaction,
    )

    confirmation_thread.start()

    assert confirmation_ready.wait(timeout=5)

    completion_thread.start()

    assert completion_started.wait(timeout=5)

    # complete_booking() должен ждать освобождения row lock.
    assert not completion_finished.wait(timeout=0.5)

    release_confirmation.set()

    confirmation_thread.join(timeout=5)
    completion_thread.join(timeout=5)

    assert not confirmation_thread.is_alive()
    assert not completion_thread.is_alive()
    assert thread_errors == []
    assert completion_results == [Booking.Status.COMPLETED]

    booking.refresh_from_db()

    assert booking.status == Booking.Status.COMPLETED
