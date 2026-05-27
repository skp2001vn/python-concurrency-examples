"""Book event seats from concurrent async requests.

The business logic is an async ticketing workflow: many customers may try to
book seats for the same event at the same time, and each seat can belong to at
most one confirmed booking.

The example uses `asyncio.Lock` because checking whether a seat is available
and assigning it to a booking must not interleave with another coroutine doing
the same check. The lock protects all seat and booking ownership state within
one event loop.
"""

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeatBooking:
    """SeatBooking reports one confirmed seat booking.

    Attributes:
        booking_id: Stable identifier for the booking request.
        customer_id: Stable identifier for the customer who owns the seat.
        seat_id: Stable identifier for the booked seat.
    """

    booking_id: str
    customer_id: str
    seat_id: str


class AsyncSeatBooking:
    """AsyncSeatBooking coordinates seat booking requests in one event loop.

    The service is safe for concurrent use by many async tasks. A booking ID
    may be used once, each seat may be booked by only one customer, and callers
    can inspect consistent snapshots of booked and available seats.
    """

    def __init__(self, seat_ids: set[str]) -> None:
        """Create a booking service for the supplied seats."""
        if not seat_ids:
            raise ValueError("seat_ids must not be empty")
        if any(not seat_id for seat_id in seat_ids):
            raise ValueError("seat_ids must not contain empty values")

        self._lock = asyncio.Lock()
        self._seat_ids = frozenset(seat_ids)
        self._bookings_by_id: dict[str, SeatBooking] = {}
        self._booking_ids_by_seat: dict[str, str] = {}

    async def book(
        self,
        booking_id: str,
        customer_id: str,
        seat_id: str,
    ) -> bool:
        """Book one seat and return whether the booking was confirmed."""
        if not booking_id:
            raise ValueError("booking_id must not be empty")
        if not customer_id:
            raise ValueError("customer_id must not be empty")
        if seat_id not in self._seat_ids:
            raise ValueError("seat_id must be a known seat")

        async with self._lock:
            if booking_id in self._bookings_by_id:
                return False
            if seat_id in self._booking_ids_by_seat:
                return False

            booking = SeatBooking(
                booking_id=booking_id,
                customer_id=customer_id,
                seat_id=seat_id,
            )
            self._bookings_by_id[booking_id] = booking
            self._booking_ids_by_seat[seat_id] = booking_id
            return True

    async def cancel(self, booking_id: str) -> bool:
        """Cancel a booking and return whether a confirmed booking was removed."""
        if not booking_id:
            raise ValueError("booking_id must not be empty")

        async with self._lock:
            booking = self._bookings_by_id.pop(booking_id, None)
            if booking is None:
                return False

            del self._booking_ids_by_seat[booking.seat_id]
            return True

    async def booking_for_seat(self, seat_id: str) -> SeatBooking | None:
        """Return the booking for a seat, or `None` if the seat is available."""
        if seat_id not in self._seat_ids:
            raise ValueError("seat_id must be a known seat")

        async with self._lock:
            booking_id = self._booking_ids_by_seat.get(seat_id)
            if booking_id is None:
                return None
            return self._bookings_by_id[booking_id]

    async def booked_seats(self) -> frozenset[str]:
        """Return a consistent snapshot of booked seat IDs."""
        async with self._lock:
            return frozenset(self._booking_ids_by_seat)

    async def available_seats(self) -> frozenset[str]:
        """Return a consistent snapshot of available seat IDs."""
        async with self._lock:
            return self._seat_ids.difference(self._booking_ids_by_seat)
