import sure  # noqa # pylint: disable=unused-import

from moto.moto_api._internal.state_manager import StateManager


def test_public_api():
    from moto.moto_api import state_manager

    state_manager.should.be.a(StateManager)


def test_default_transition():
    manager = StateManager()

    manager.register_default_transition(
        model_name="dax::cluster", transition={"progression": "manual"}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    actual.should.equal({"progression": "manual"})


def test_set_transition():
    manager = StateManager()

    manager.set_transition(
        model_name="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    actual.should.equal({"progression": "waiter", "wait_times": 3})


def test_set_transition_overrides_default():
    manager = StateManager()

    manager.register_default_transition(
        model_name="dax::cluster", transition={"progression": "manual"}
    )

    manager.set_transition(
        model_name="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    actual.should.equal({"progression": "waiter", "wait_times": 3})


def test_unset_transition():
    manager = StateManager()

    manager.register_default_transition(
        model_name="dax::cluster", transition={"progression": "manual"}
    )

    manager.set_transition(
        model_name="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    manager.unset_transition(model_name="dax::cluster")

    actual = manager.get_transition(model_name="dax::cluster")
    actual.should.equal({"progression": "manual"})


def test_get_default_transition():
    manager = StateManager()

    actual = manager.get_transition(model_name="unknown")
    actual.should.equal({"progression": "immediate"})


def test_get_registered_models():
    manager = StateManager()

    manager.get_registered_models().should.equal([])
