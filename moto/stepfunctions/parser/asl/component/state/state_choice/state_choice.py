from typing import Optional

from moto.stepfunctions.parser.api import HistoryEventType
from moto.stepfunctions.parser.asl.component.common.flow.end import End
from moto.stepfunctions.parser.asl.component.common.flow.next import Next
from moto.stepfunctions.parser.asl.component.state.state import CommonStateField
from moto.stepfunctions.parser.asl.component.state.state_choice.choices_decl import (
    ChoicesDecl,
)
from moto.stepfunctions.parser.asl.component.state.state_choice.default_decl import (
    DefaultDecl,
)
from moto.stepfunctions.parser.asl.component.state.state_props import StateProps
from moto.stepfunctions.parser.asl.eval.environment import Environment


class StateChoice(CommonStateField):
    choices_decl: ChoicesDecl

    def __init__(self):
        super(StateChoice, self).__init__(
            state_entered_event_type=HistoryEventType.ChoiceStateEntered,
            state_exited_event_type=HistoryEventType.ChoiceStateExited,
        )
        self.default_state: Optional[DefaultDecl] = None
        self._next_state_name: Optional[str] = None

    def from_state_props(self, state_props: StateProps) -> None:
        super(StateChoice, self).from_state_props(state_props)
        self.choices_decl = state_props.get(ChoicesDecl)
        self.default_state = state_props.get(DefaultDecl)

        if state_props.get(Next) or state_props.get(End):
            raise ValueError(
                "Choice states don't support the End field. "
                "In addition, they use Next only inside their Choices field. "
                f"With state '{self}'."
            )

    def _set_next(self, env: Environment) -> None:
        if self._next_state_name is None:
            raise RuntimeError(f"No Next option from state: '{self}'.")
        env.next_state_name = self._next_state_name

    def _eval_state(self, env: Environment) -> None:
        if self.default_state:
            self._next_state_name = self.default_state.state_name

        # TODO: Lazy evaluation?
        for rule in self.choices_decl.rules:
            rule.eval(env)
            res = env.stack.pop()
            if res is True:
                if not rule.next_stmt:
                    raise RuntimeError(
                        f"Missing Next definition for state_choice rule '{rule}' in choices '{self}'."
                    )
                self._next_state_name = rule.next_stmt.name
                break
