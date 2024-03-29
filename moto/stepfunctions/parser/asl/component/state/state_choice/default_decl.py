from typing import Final

from moto.stepfunctions.parser.asl.component.component import Component


class DefaultDecl(Component):
    def __init__(self, state_name: str):
        self.state_name: Final[str] = state_name
