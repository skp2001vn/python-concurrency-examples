"""Unit tests for the asyncseatbooking example.

The example models async ticketing requests that try to book seats for an
event. The tests verify caller-facing behavior: invalid seats are rejected,
duplicate booking requests do not change ownership, booked seats can be
cancelled, snapshots are consistent, and concurrent requests cannot book the
same seat twice.
"""

import asyncio
import unittest

from python_concurrency_examples.examples.asyncseatbooking import (
    AsyncSeatBooking,
    SeatBooking,
)


class AsyncSeatBookingTest(unittest.IsolatedAsyncioTestCase):
    """AsyncSeatBookingTest verifies the public async booking behavior."""

    # Verifies that the service requires at least one known seat.
    async def test_rejects_empty_seat_set(self) -> None:
        with self.assertRaises(ValueError):
            AsyncSeatBooking(set())

    # Verifies that all configured seat IDs must be non-empty.
    async def test_rejects_empty_seat_id(self) -> None:
        with self.assertRaises(ValueError):
            AsyncSeatBooking({"A1", ""})

    # Verifies that a booking request must include a booking ID.
    async def test_rejects_empty_booking_id(self) -> None:
        booking = AsyncSeatBooking({"A1"})

        with self.assertRaises(ValueError):
            await booking.book("", customer_id="customer-1", seat_id="A1")

    # Verifies that a booking request must include a customer ID.
    async def test_rejects_empty_customer_id(self) -> None:
        booking = AsyncSeatBooking({"A1"})

        with self.assertRaises(ValueError):
            await booking.book("booking-1", customer_id="", seat_id="A1")

    # Verifies that callers cannot book seats outside the configured event.
    async def test_rejects_unknown_seat_id(self) -> None:
        booking = AsyncSeatBooking({"A1"})

        with self.assertRaises(ValueError):
            await booking.book("booking-1", customer_id="customer-1", seat_id="B1")

    # Verifies that a successful booking owns the requested seat.
    async def test_books_available_seat(self) -> None:
        booking = AsyncSeatBooking({"A1", "A2"})

        confirmed = await booking.book(
            "booking-1",
            customer_id="customer-1",
            seat_id="A1",
        )

        self.assertTrue(confirmed)
        self.assertEqual(
            await booking.booking_for_seat("A1"),
            SeatBooking(
                booking_id="booking-1",
                customer_id="customer-1",
                seat_id="A1",
            ),
        )
        self.assertEqual(await booking.booked_seats(), frozenset({"A1"}))
        self.assertEqual(await booking.available_seats(), frozenset({"A2"}))

    # Verifies that duplicate booking IDs are ignored.
    async def test_duplicate_booking_id_does_not_book_second_seat(self) -> None:
        booking = AsyncSeatBooking({"A1", "A2"})

        self.assertTrue(
            await booking.book("booking-1", customer_id="customer-1", seat_id="A1")
        )
        self.assertFalse(
            await booking.book("booking-1", customer_id="customer-1", seat_id="A2")
        )

        self.assertEqual(await booking.booked_seats(), frozenset({"A1"}))
        self.assertIsNone(await booking.booking_for_seat("A2"))

    # Verifies that a seat cannot be owned by two booking IDs.
    async def test_booked_seat_cannot_be_booked_again(self) -> None:
        booking = AsyncSeatBooking({"A1"})

        self.assertTrue(
            await booking.book("booking-1", customer_id="customer-1", seat_id="A1")
        )
        self.assertFalse(
            await booking.book("booking-2", customer_id="customer-2", seat_id="A1")
        )

        self.assertEqual(
            await booking.booking_for_seat("A1"),
            SeatBooking(
                booking_id="booking-1",
                customer_id="customer-1",
                seat_id="A1",
            ),
        )

    # Verifies that cancellation frees a seat for a later booking.
    async def test_cancel_frees_seat_for_later_booking(self) -> None:
        booking = AsyncSeatBooking({"A1"})

        self.assertTrue(
            await booking.book("booking-1", customer_id="customer-1", seat_id="A1")
        )
        self.assertTrue(await booking.cancel("booking-1"))
        self.assertFalse(await booking.cancel("booking-1"))

        self.assertIsNone(await booking.booking_for_seat("A1"))
        self.assertTrue(
            await booking.book("booking-2", customer_id="customer-2", seat_id="A1")
        )

    # Verifies that concurrent requests confirm only one owner for one seat.
    async def test_concurrent_requests_for_same_seat_confirm_once(self) -> None:
        request_count = 25
        booking = AsyncSeatBooking({"A1"})
        ready_count = 0
        ready = asyncio.Event()
        release = asyncio.Event()
        ready_lock = asyncio.Lock()

        async def try_book(index: int) -> bool:
            nonlocal ready_count
            async with ready_lock:
                ready_count += 1
                if ready_count == request_count:
                    ready.set()

            await release.wait()
            return await booking.book(
                f"booking-{index}",
                customer_id=f"customer-{index}",
                seat_id="A1",
            )

        tasks = [asyncio.create_task(try_book(index)) for index in range(request_count)]
        await asyncio.wait_for(ready.wait(), timeout=1)
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=1)

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), request_count - 1)
        self.assertEqual(await booking.booked_seats(), frozenset({"A1"}))

    # Verifies that concurrent requests for different seats can all succeed.
    async def test_concurrent_requests_for_different_seats_all_confirm(self) -> None:
        seat_count = 10
        seat_ids = {f"A{index}" for index in range(seat_count)}
        booking = AsyncSeatBooking(seat_ids)

        results = await asyncio.gather(
            *(
                booking.book(
                    f"booking-{index}",
                    customer_id=f"customer-{index}",
                    seat_id=f"A{index}",
                )
                for index in range(seat_count)
            )
        )

        self.assertEqual(results.count(True), seat_count)
        self.assertEqual(await booking.booked_seats(), frozenset(seat_ids))
        self.assertEqual(await booking.available_seats(), frozenset())


if __name__ == "__main__":
    unittest.main()
