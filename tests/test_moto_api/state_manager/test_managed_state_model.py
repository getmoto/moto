import sure  # noqa # pylint: disable=unused-import

from moto.moto_api._internal.managed_state_model import ManagedState
from moto.moto_api import state_manager


class ExampleModel(ManagedState):
    def __init__(self):
        super().__init__(
            model_name="example::model", transitions=[("frist_status", "second_status")]
        )

    state_manager.register_default_transition(
        model_name="example::model", transition={"progression": "manual", "times": 999}
    )


def test_initial_state():
    ExampleModel().status.should.equal("frist_status")


def test_advancing_without_specifying_configuration_does_nothing():
    model = ExampleModel()
    for _ in range(5):
        model.status.should.equal("frist_status")
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

    model.status.should.equal("fifth")

    model.advance()

    model.status.should.equal("fifth")


def test_advance_x_times():
    model = ExampleModel()
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "manual", "times": 3}
    )
    for _ in range(2):
        model.advance()
        model.status.should.equal("frist_status")

    # 3rd time is a charm
    model.advance()
    model.status.should.equal("second_status")

    # Status is still the same if we keep asking for it
    model.status.should.equal("second_status")

    # Advancing more does not make a difference - there's nothing to advance to
    model.advance()
    model.status.should.equal("second_status")


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

    model.status.should.equal("frist_status")
    model.status.should.equal("frist_status")
    model.advance()
    model.status.should.equal("second")
    model.status.should.equal("second")
    model.advance()
    model.status.should.equal("third")
    model.status.should.equal("third")
    model.advance()
    model.status.should.equal("fourth")
    model.status.should.equal("fourth")
    model.advance()
    model.status.should.equal("fifth")
    model.status.should.equal("fifth")


def test_override_status():
    model = ExampleModel()
    model.status = "creating"
    model._transitions = [("creating", "ready"), ("updating", "ready")]
    state_manager.set_transition(
        model_name="example::model", transition={"progression": "manual", "times": 1}
    )

    model.status.should.equal("creating")
    model.advance()
    model.status.should.equal("ready")
    model.advance()
    # We're still ready
    model.status.should.equal("ready")

    # Override status manually
    model.status = "updating"

    model.status.should.equal("updating")
    model.advance()
    model.status.should.equal("ready")
    model.status.should.equal("ready")
    model.advance()
    model.status.should.equal("ready")


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

    model.status.should.equal("first")
    # The status will stick to 'first' for a long time
    # Advancing the model doesn't do anything, really
    for _ in range(10):
        model.advance()
        model.status.should.equal("first")

    import time

    time.sleep(2)
    # Status has only progressed after 2 seconds have passed
    model.status.should.equal("second")
