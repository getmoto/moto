"""
This module provides a Shape subclass to encapsulate service model error definitions.

It also provides a mechanism for mapping ServiceException exception classes to the
corresponding error shape defined in the relevant service model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from warnings import warn

from moto.core.model import StructureShape

if TYPE_CHECKING:
    from moto.core.model import ServiceModel

# These are common error codes that are *not* included in the service definitions.
# For example:
# https://docs.aws.amazon.com/emr/latest/APIReference/CommonErrors.html
# https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/CommonErrors.html
# https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/CommonErrors.html
# TODO: Augment the service definitions with shape models for these errors.
COMMON_ERROR_CODES = [
    "InvalidParameterCombination",
    "InvalidParameterException",
    "InvalidParameterValue",
    "ValidationError",
    "ValidationException",
]


class ErrorShape(StructureShape):
    _shape_model: dict[str, Any]

    @property
    def error_code(self) -> str:
        code = str(super().error_code)
        return code

    @property
    def is_sender_fault(self) -> bool:
        internal_fault = self._shape_model.get("fault", False)
        error_info = self.metadata.get("error", {})
        sender_fault = error_info.get("senderFault", False)
        return sender_fault or not internal_fault

    @property
    def namespace(self) -> str | None:
        return self.metadata.get("error", {}).get("namespace")


class ErrorLookup:
    def __init__(
        self, code_to_error: dict[str, ErrorShape], service_model: ServiceModel
    ) -> None:
        self._code_to_error = code_to_error
        self._service_id = service_model.metadata.get("serviceId")

    def from_exception(self, exception: Exception) -> ErrorShape:
        code = getattr(exception, "code", exception.__class__.__name__)
        error = self._code_to_error.get(code)
        if error is None:
            if self._service_id and code not in COMMON_ERROR_CODES:
                warning = f"{self._service_id} service model does not contain an error shape that matches code {code} from Exception({exception.__class__.__name__})"
                warn(warning)
            error = ErrorShape(
                shape_name=exception.__class__.__name__,
                shape_model={
                    "exception": True,
                    "type": "structure",
                    "members": {},
                    "error": {
                        "code": code,
                    },
                },
            )
        return error


class ErrorLookupFactory:
    def __init__(self) -> None:
        self._error_lut_cache: dict[str, ErrorLookup] = {}

    def for_service(self, service_model: ServiceModel) -> ErrorLookup:
        service_id = service_model.metadata.get("serviceId")
        if service_id not in self._error_lut_cache:
            error_lut = self._create_error_lut(service_model)
            if service_id is None:
                return error_lut
            self._error_lut_cache[service_id] = error_lut
        return self._error_lut_cache[service_id]

    @staticmethod
    def _create_error_lut(service_model: ServiceModel) -> ErrorLookup:
        """We map an error's code, name, and any alias codes to the same ErrorShape."""
        code_to_shape = {}
        for shape in service_model.error_shapes:
            error_shape = ErrorShape(
                shape.name,
                shape._shape_model,  # type: ignore[attr-defined]
                shape._shape_resolver,  # type: ignore[attr-defined]
            )
            code_to_shape[error_shape.name] = error_shape
            code_to_shape[error_shape.error_code] = error_shape
            for error_code in error_shape.error_code_aliases:
                code_to_shape[error_code] = error_shape
        return ErrorLookup(code_to_shape, service_model)
