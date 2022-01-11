from threading import Timer as ThreadingTimer

from moto.swf.models import Timer
from unittest.mock import Mock


def test_timer_creation():
    background_timer = ThreadingTimer(30.0, lambda x: x)
    under_test = Timer(background_timer, "abc123")

    assert under_test.background_timer == background_timer
    assert under_test.started_event_id == "abc123"


def test_timer_start_delegates_to_wrapped_timer():
    background_timer = ThreadingTimer(30.0, lambda x: x)
    background_timer.start = Mock()
    under_test = Timer(background_timer, "abc123")

    under_test.start()

    background_timer.start.assert_called_once()


def test_timer_aliveness_delegates_to_wrapped_timer():
    background_timer = ThreadingTimer(30.0, lambda x: x)
    background_timer.is_alive = Mock()
    under_test = Timer(background_timer, "abc123")

    under_test.is_alive()

    background_timer.is_alive.assert_called_once()


def test_timer_cancel_delegates_to_wrapped_timer():
    background_timer = ThreadingTimer(30.0, lambda x: x)
    background_timer.cancel = Mock()
    under_test = Timer(background_timer, "abc123")

    under_test.cancel()

    background_timer.cancel.assert_called_once()
