"""
This module provides a facade over the `botocore.model` module.

It defines custom shape and service model classes that extend Botocore's
classes to add additional functionality and properties specific to Moto.

Because Botocore's shape classes are not designed for subclassing, this module
redefines the class hierarchy to ensure that all shape classes inherit from
both the relevant Botocore shape class as well as a new Moto base class.
This allows us to add common functionality to all shape types while still
retaining the original behavior of the Botocore classes without monkey-patching.

This module also defines a modified ShapeResolver to ensure that all shapes created
through the resolver are instances of our custom classes.

Any Moto code that needs to interact with Botocore's model classes should do so
through this facade to avoid direct dependencies on Botocore's internal structure,
which may change over time.
"""

from __future__ import annotations

import warnings
from typing import Any, Mapping, cast

from botocore.model import ListShape as BotocoreListShape
from botocore.model import MapShape as BotocoreMapShape
from botocore.model import OperationModel as BotocoreOperationModel
from botocore.model import ServiceModel as BotocoreServiceModel
from botocore.model import Shape as BotocoreShape
from botocore.model import ShapeResolver as BotocoreShapeResolver
from botocore.model import StringShape as BotocoreStringShape
from botocore.model import StructureShape as BotocoreStructureShape
from botocore.utils import CachedProperty, instance_cache

# These are common error codes that are *not* included in the service definitions.
# For example:
# https://docs.aws.amazon.com/emr/latest/APIReference/CommonErrors.html
# https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/CommonErrors.html
# TODO: Augment the service definitions with shape models for these errors.
COMMON_ERROR_CODES = [
    "InvalidParameterCombination",
    "InvalidParameterException",
    "InvalidParameterValue",
    "ValidationError",
    "ValidationException",
]

class Shape(BotocoreShape):
    # Custom Moto model properties that we want available in the serialization dict.
    SERIALIZED_ATTRS = BotocoreShape.SERIALIZED_ATTRS + [
        "locationNameForQueryCompatibility"
    ]

class ShapeExtensionMethodsMixin:
    serialization: dict[str, Any]

    def get_serialized_name(self, default_name: str) -> str:
        return self.serialization.get("name", default_name)

    def get_query_compatible_name(self, default_name: str) -> str:
        shape_data = getattr(self, "_shape_model", {})
        query_compatible_name = shape_data.get("locationNameForQueryCompatibility")
        if query_compatible_name:
            return query_compatible_name
        return default_name

    @property
    def is_flattened(self) -> bool:
        return self.serialization.get("flattened", False)

    @property
    def is_http_header_trait(self) -> bool:
        return self.serialization.get("location") in ["header", "headers"]

    @property
    def is_not_bound_to_body(self) -> bool:
        return "location" in self.serialization

class Shape(BotocoreShape, ShapeExtensionMethodsMixin):
    pass

class StringShape(BotocoreStringShape, Shape):
    pass


class ListShape(BotocoreListShape, Shape):
    pass


class MapShape(BotocoreMapShape, Shape):
    pass


class StructureShape(BotocoreStructureShape, Shape):
    @CachedProperty
    def members(self) -> dict[str, Shape]:  # type: ignore[override]
        return cast(dict[str, Shape], super().members)

    @CachedProperty
    def error_code_aliases(self) -> list[str]:
        if not self.metadata.get("exception", False):
            return []
        error_metadata = self.metadata.get("error", {})
        aliases = error_metadata.get("codeAliases", [])
        return aliases

class ErrorShape(StructureShape):
    _shape_model: dict[str, Any]

    @property
    def is_sender_fault(self) -> bool:
        internal_fault = self._shape_model.get("fault", False)
        error_info = self.metadata.get("error", {})
        sender_fault = error_info.get("senderFault", False)
        return sender_fault or not internal_fault

    # Overriding super class property to keep mypy happy...
    @property
    def error_code(self) -> str:
        code = str(super().error_code)
        return code

    @property
    def error_message(self) -> str:
        error_info = self.metadata.get("error", {})
        error_message = error_info.get("message", "")
        return error_message

    @property
    def namespace(self) -> str | None:
        return self.metadata.get("error", {}).get("namespace")

    @classmethod
    def from_existing_shape(cls, shape: StructureShape) -> ErrorShape:
        return cls(shape.name, shape._shape_model, shape._shape_resolver)  # type: ignore[attr-defined]


class ServiceModel(BotocoreServiceModel):
    def __init__(
        self, service_description: Mapping[str, Any], service_name: str | None = None
    ):
        super(ServiceModel, self).__init__(service_description, service_name)
        # Use our custom shape resolver.
        self._shape_resolver = ShapeResolver(service_description.get("shapes", {}))

    @instance_cache
    def operation_model(self, operation_name: str) -> OperationModel:  # type: ignore[misc]
        operation_model = super().operation_model(operation_name)
        model = getattr(operation_model, "_operation_model", {})
        return OperationModel(model, self, operation_name)

    @CachedProperty
    def is_query_compatible(self) -> bool:
        return "awsQueryCompatible" in self.metadata

    def get_error_shape(self, error: Exception) -> ErrorShape:
        error_code = getattr(error, "code", "UnknownError")
        error_name = error.__class__.__name__
        error_shapes = cast(list[ErrorShape], self.error_shapes)
        for error_shape in error_shapes:
            if error_shape.error_code == error_code:
                break
            if error_shape.name in [error_code, error_name]:
                break
            aliases = error_shape.metadata.get("error", {}).get("aliasCodes", [])
            if error_code in aliases or error_name in aliases:
                break
        else:
            error_shape = None
        if error_shape is None:
            service_id = self.metadata.get("serviceId")
            if service_id and error_code not in COMMON_ERROR_CODES:
                warning = f"{service_id} service model does not contain an error shape that matches code {error_code} from Exception({error_name})"
                warnings.warn(warning)
            generic_error_model = {
                "exception": True,
                "type": "structure",
                "members": {},
                "error": {
                    "code": error_code,
                },
            }
            error_shape = ErrorShape(error_code, generic_error_model)
        else:
            error_shape = ErrorShape.from_existing_shape(error_shape)
        return error_shape


class OperationModel(BotocoreOperationModel):
    _operation_model: dict[str, Any]
    _service_model: ServiceModel

    @property
    def service_model(self) -> ServiceModel:
        return self._service_model


class ShapeResolver(BotocoreShapeResolver):
    SHAPE_CLASSES = {
        "structure": StructureShape,  # type: ignore[dict-item]
        "list": ListShape,  # type: ignore[dict-item]
        "map": MapShape,  # type: ignore[dict-item]
        "string": StringShape,  # type: ignore[dict-item]
    }

    def get_shape_by_name(
        self, shape_name: str, member_traits: Mapping[str, Any] | None = None
    ) -> Shape:
        shape = super().get_shape_by_name(shape_name, member_traits)
        # The SHAPE_CLASSES dict only allows us to override Shape subclasses,
        # but Botocore will return its own Shape base class for unknown types.
        # If the returned shape is not a part of our hierarchy, we need to
        # convert it to our Shape base class here.
        if not isinstance(shape, Shape):
            shape = Shape(shape_name, getattr(shape, "_shape_model", {}), self)
        return shape
