"""Exceptions raised by the codepipeline service."""

from moto.core.exceptions import ServiceException


class CodePipelineException(ServiceException):
    pass


class InvalidStructureException(CodePipelineException):
    code = "InvalidStructureException"


class PipelineNotFoundException(CodePipelineException):
    code = "PipelineNotFoundException"


class PipelineExecutionNotFoundException(CodePipelineException):
    code = "PipelineExecutionNotFoundException"


class ResourceNotFoundException(CodePipelineException):
    code = "ResourceNotFoundException"


class InvalidTagsException(CodePipelineException):
    code = "InvalidTagsException"


class TooManyTagsException(CodePipelineException):
    code = "TooManyTagsException"

    def __init__(self, arn: str):
        super().__init__(f"Tag limit exceeded for resource [{arn}].")
