from moto.moto_api._internal.state_manager import StateManager


def test_public_api():
    from moto.moto_api import state_manager

    assert isinstance(state_manager, StateManager)


def test_default_transition():
    manager = StateManager()

    manager.register_default_transition(
        model_name="dax::cluster", transition={"progression": "manual"}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    assert actual == {"progression": "manual"}


def test_set_transition():
    manager = StateManager()

    manager.set_transition(
        model_name="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    assert actual == {"progression": "waiter", "wait_times": 3}


def test_set_transition_overrides_default():
    manager = StateManager()

    manager.register_default_transition(
        model_name="dax::cluster", transition={"progression": "manual"}
    )

    manager.set_transition(
        model_name="dax::cluster", transition={"progression": "waiter", "wait_times": 3}
    )

    actual = manager.get_transition(model_name="dax::cluster")
    assert actual == {"progression": "waiter", "wait_times": 3}


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
    assert actual == {"progression": "manual"}


def test_get_default_transition():
    manager = StateManager()

    actual = manager.get_transition(model_name="unknown")
    assert actual == {"progression": "immediate"}


def test_get_registered_models():
    manager = StateManager()

    assert manager.get_registered_models() == []
