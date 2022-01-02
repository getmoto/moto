import sure  # noqa # pylint: disable=unused-import

from moto.moto_api._internal.state_manager import StateManager


def test_public_api():
    from moto.moto_api import state_manager

    state_manager.should.be.a(StateManager)


def test_set_transition():
    manager = StateManager()

    manager.set_transition(
        feature="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    actual = manager.get_transition(feature="dax::cluster")
    actual.should.equal({"progression": "waiter", "wait_times": 3})


def test_get_default_transition():
    manager = StateManager()

    actual = manager.get_transition(feature="unknown")
    actual.should.equal({"progression": "immediate"})
