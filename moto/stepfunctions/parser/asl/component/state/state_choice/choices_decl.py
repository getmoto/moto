from typing import Final, List

from moto.stepfunctions.parser.asl.component.component import Component
from moto.stepfunctions.parser.asl.component.state.state_choice.choice_rule import (
    ChoiceRule,
)


class ChoicesDecl(Component):
    def __init__(self, rules: List[ChoiceRule]):
        self.rules: Final[List[ChoiceRule]] = rules
