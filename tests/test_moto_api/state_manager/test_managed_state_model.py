from moto.moto_api import state_manager
from moto.moto_api._internal.managed_state_model import ManagedState


class ExampleModel(ManagedState):
    def __init__(self):
        super().__init__(
            model_name="example::model", transitions=[("frist_status", "second_status")]
        )

    state_manager.register_default_transition(
        model_name="example::model", transition={"progression": "manual", "times": 999}
    )


def test_initial_state():
    assert ExampleModel().status == "frist_status"


def test_advancing_without_specifying_configuration_does_nothing():
    model = ExampleModel()
    for _ in range(5):
        assert model.status == "frist_status"
        model.advance()


def test_advance_immediately():
    model = ExampleModel()
    model._transitions = [
        ("frist_status", "second"),
        ("second", "third"),
        ("third", "fourth"),
        ("fourth", "fifth"),
    ]
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "immediate"}
    )

    assert model.status == "fifth"

    model.advance()

    assert model.status == "fifth"


def test_advance_x_times():
    model = ExampleModel()
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "manual", "times": 3}
    )
    for _ in range(2):
        model.advance()
        assert model.status == "frist_status"

    # 3rd time is a charm
    model.advance()
    assert model.status == "second_status"

    # Status is still the same if we keep asking for it
    assert model.status == "second_status"

    # Advancing more does not make a difference - there's nothing to advance to
    model.advance()
    assert model.status == "second_status"


def test_advance_multiple_stages():
    model = ExampleModel()
    model._transitions = [
        ("frist_status", "second"),
        ("second", "third"),
        ("third", "fourth"),
        ("fourth", "fifth"),
    ]
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "manual", "times": 1}
    )

    assert model.status == "frist_status"
    assert model.status == "frist_status"
    model.advance()
    assert model.status == "second"
    assert model.status == "second"
    model.advance()
    assert model.status == "third"
    assert model.status == "third"
    model.advance()
    assert model.status == "fourth"
    assert model.status == "fourth"
    model.advance()
    assert model.status == "fifth"
    assert model.status == "fifth"


def test_override_status():
    model = ExampleModel()
    model.status = "creating"
    model._transitions = [("creating", "ready"), ("updating", "ready")]
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "manual", "times": 1}
    )

    assert model.status == "creating"
    model.advance()
    assert model.status == "ready"
    model.advance()
    # We're still ready
    assert model.status == "ready"

    # Override status manually
    model.status = "updating"

    assert model.status == "updating"
    model.advance()
    assert model.status == "ready"
    assert model.status == "ready"
    model.advance()
    assert model.status == "ready"


class SlowModel(ManagedState):
    def __init__(self):
        super().__init__(
            model_name="example::slowmodel", transitions=[("first", "second")]
        )


def test_realworld_delay():
    model = SlowModel()
    state_manager.set_transition(
        model_name="example::slowmodel",
        transition={"progression": "time", "seconds": 2},
    )

    assert model.status == "first"
    # The status will stick to 'first' for a long time
    # Advancing the model doesn't do anything, really
    for _ in range(10):
        model.advance()
        assert model.status == "first"

    import time

    time.sleep(2)
    # Status has only progressed after 2 seconds have passed
    assert model.status == "second"
