import importlib
import sys
from typing import TYPE_CHECKING, Iterable, Tuple

import moto

if TYPE_CHECKING:
    from moto.core import BackendDict, BaseBackend


decorators = [d for d in dir(moto) if d.startswith("mock_") and not d == "mock_all"]
decorator_functions = [getattr(moto, f) for f in decorators]
BACKENDS = {f.boto3_name: (f.name, f.backend) for f in decorator_functions}
BACKENDS["dynamodb_v20111205"] = ("dynamodb_v20111205", "dynamodb_backends")
BACKENDS["moto_api"] = ("moto_api._internal", "moto_api_backends")
BACKENDS["instance_metadata"] = ("instance_metadata", "instance_metadata_backends")
BACKENDS["s3bucket_path"] = ("s3", "s3_backends")


def _import_backend(
    module_name: str,
    backends_name: str,
) -> "BackendDict[BaseBackend]":
    module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


def backends() -> "Iterable[BackendDict[BaseBackend]]":
    for module_name, backends_name in BACKENDS.values():
        yield _import_backend(module_name, backends_name)


def service_backends() -> "Iterable[BackendDict[BaseBackend]]":
    services = [(f.name, f.backend) for f in decorator_functions]
    for module_name, backends_name in sorted(set(services)):
        yield _import_backend(module_name, backends_name)


def loaded_backends() -> "Iterable[Tuple[str, BackendDict[BaseBackend]]]":
    loaded_modules = sys.modules.keys()
    moto_modules = [m for m in loaded_modules if m.startswith("moto.")]
    imported_backends = [
        name
        for name, (module_name, _) in BACKENDS.items()
        if f"moto.{module_name}" in moto_modules
    ]
    for name in imported_backends:
        module_name, backends_name = BACKENDS[name]
        yield name, _import_backend(module_name, backends_name)


def get_backend(name: str) -> "BackendDict[BaseBackend]":
    module_name, backends_name = BACKENDS[name]
    return _import_backend(module_name, backends_name)
