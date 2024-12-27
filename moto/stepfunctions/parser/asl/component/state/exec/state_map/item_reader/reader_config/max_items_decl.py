import abc
from typing import Final

from moto.stepfunctions.parser.api import ExecutionFailedEventDetails, HistoryEventType
from moto.stepfunctions.parser.asl.component.common.error_name.failure_event import (
    FailureEvent,
    FailureEventException,
)
from moto.stepfunctions.parser.asl.component.common.error_name.states_error_name import (
    StatesErrorName,
)
from moto.stepfunctions.parser.asl.component.common.error_name.states_error_name_type import (
    StatesErrorNameType,
)
from moto.stepfunctions.parser.asl.component.common.jsonata.jsonata_template_value_terminal import (
    JSONataTemplateValueTerminalExpression,
)
from moto.stepfunctions.parser.asl.component.common.variable_sample import (
    VariableSample,
)
from moto.stepfunctions.parser.asl.component.eval_component import EvalComponent
from moto.stepfunctions.parser.asl.eval.environment import Environment
from moto.stepfunctions.parser.asl.eval.event.event_detail import EventDetails
from moto.stepfunctions.parser.asl.utils.json_path import extract_json


class MaxItemsDecl(EvalComponent, abc.ABC):
    """
    "MaxItems": Limits the number of data items passed to the Map state. For example, suppose that you provide a
    CSV file that contains 1000 rows and specify a limit of 100. Then, the interpreter passes only 100 rows to the
    Map state. The Map state processes items in sequential order, starting after the header row.
    Currently, you can specify a limit of up to 100,000,000
    """

    MAX_VALUE: Final[int] = 100_000_000

    def _clip_value(self, value: int) -> int:
        if value == 0:
            return self.MAX_VALUE
        return min(value, self.MAX_VALUE)

    @abc.abstractmethod
    def _get_value(self, env: Environment) -> int: ...

    def _eval_body(self, env: Environment) -> None:
        max_items: int = self._get_value(env=env)
        max_items = self._clip_value(max_items)
        env.stack.append(max_items)


class MaxItems(MaxItemsDecl):
    max_items: Final[int]

    def __init__(self, max_items: int = MaxItemsDecl.MAX_VALUE):
        if max_items < 0 or max_items > MaxItems.MAX_VALUE:
            raise ValueError(
                f"MaxItems value MUST be a non-negative integer "
                f"non greater than '{MaxItems.MAX_VALUE}', got '{max_items}'."
            )
        self.max_items = max_items

    def _get_value(self, env: Environment) -> int:
        return self.max_items


class MaxItemsJSONata(MaxItemsDecl):
    jsonata_template_value_terminal_expression: Final[
        JSONataTemplateValueTerminalExpression
    ]

    def __init__(
        self,
        jsonata_template_value_terminal_expression: JSONataTemplateValueTerminalExpression,
    ):
        super().__init__()
        self.jsonata_template_value_terminal_expression = (
            jsonata_template_value_terminal_expression
        )

    def _get_value(self, env: Environment) -> int:
        # TODO: add snapshot tests to verify AWS's behaviour about non integer values.
        self.jsonata_template_value_terminal_expression.eval(env=env)
        max_items: int = int(env.stack.pop())
        return max_items


class MaxItemsPathVar(MaxItemsDecl):
    variable_sample: VariableSample

    def __init__(self, variable_sample: VariableSample):
        super().__init__()
        self.variable_sample = variable_sample

    def _get_value(self, env: Environment) -> int:
        self.variable_sample.eval(env=env)
        # TODO: add snapshot tests to verify AWS's behaviour about non integer values.
        max_items: int = int(env.stack.pop())
        return max_items


class MaxItemsPath(MaxItemsDecl):
    """
    "MaxItemsPath": computes a MaxItems value equal to the reference path it points to.
    """

    def __init__(self, path: str):
        self.path: Final[str] = path

    def _validate_value(self, env: Environment, value: int) -> None:
        if not isinstance(value, int):
            # TODO: Note, this error appears to be validated at a earlier stage in AWS Step Functions, unlike the
            #  negative integer check that is validated at this exact depth.
            error_typ = StatesErrorNameType.StatesItemReaderFailed
            raise FailureEventException(
                failure_event=FailureEvent(
                    env=env,
                    error_name=StatesErrorName(typ=error_typ),
                    event_type=HistoryEventType.ExecutionFailed,
                    event_details=EventDetails(
                        executionFailedEventDetails=ExecutionFailedEventDetails(
                            error=error_typ.to_name(),
                            cause=(
                                f"The MaxItemsPath field refers to value '{value}' "
                                f"which is not a valid integer: {self.path}"
                            ),
                        )
                    ),
                )
            )
        if value < 0:
            error_typ = StatesErrorNameType.StatesItemReaderFailed
            raise FailureEventException(
                failure_event=FailureEvent(
                    env=env,
                    error_name=StatesErrorName(typ=error_typ),
                    event_type=HistoryEventType.MapRunFailed,
                    event_details=EventDetails(
                        executionFailedEventDetails=ExecutionFailedEventDetails(
                            error=error_typ.to_name(),
                            cause="field MaxItems must be positive",
                        )
                    ),
                )
            )

    def _get_value(self, env: Environment) -> int:
        inp = env.stack[-1]
        max_items = extract_json(self.path, inp)
        self._validate_value(env=env, value=max_items)
        return max_items
