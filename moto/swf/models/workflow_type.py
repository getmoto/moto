from .generic_type import GenericType


class WorkflowType(GenericType):
    @property
    def _configuration_keys(self):
        return [
            "defaultChildPolicy",
            "defaultExecutionStartToCloseTimeout",
            "defaultTaskStartToCloseTimeout",
            "defaultTaskPriority",
            "defaultLambdaRole",
        ]

    @property
    def kind(self):
        return "workflow"
