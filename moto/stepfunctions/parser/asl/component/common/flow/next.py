from typing import Final

from moto.stepfunctions.parser.asl.component.component import Component


class Next(Component):
    name: Final[str]

    def __init__(self, name: str):
        # The name of the next state that is run when the current state finishes.
        self.name = name
