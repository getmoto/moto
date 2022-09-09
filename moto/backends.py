import importlib
import moto
import sys


decorators = [d for d in dir(moto) if d.startswith("mock_") and not d == "mock_all"]
decorator_functions = [getattr(moto, f) for f in decorators]
BACKENDS = {f.boto3_name: (f.name, f.backend) for f in decorator_functions}
BACKENDS["dynamodb_v20111205"] = ("dynamodb_v20111205", "dynamodb_backends")
BACKENDS["moto_api"] = ("moto_api._internal", "moto_api_backends")
BACKENDS["instance_metadata"] = ("instance_metadata", "instance_metadata_backends")
BACKENDS["s3bucket_path"] = ("s3", "s3_backends")


def _import_backend(module_name, backends_name):
    module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


def backends():
    for module_name, backends_name in BACKENDS.values():
        yield _import_backend(module_name, backends_name)


def service_backends():
    services = [(f.name, f.backend) for f in decorator_functions]
    for module_name, backends_name in sorted(set(services)):
        yield _import_backend(module_name, backends_name)


def loaded_backends():
    loaded_modules = sys.modules.keys()
    loaded_modules = [m for m in loaded_modules if m.startswith("moto.")]
    imported_backends = [
        name
        for name, (module_name, _) in BACKENDS.items()
        if f"moto.{module_name}" in loaded_modules
    ]
    for name in imported_backends:
        module_name, backends_name = BACKENDS[name]
        yield name, _import_backend(module_name, backends_name)


def get_backend(name):
    module_name, backends_name = BACKENDS[name]
    return _import_backend(module_name, backends_name)


def get_model(name, region_name):
    for backends_ in backends():
        for region, backend in backends_.items():
            if region == region_name:
                models = getattr(backend.__class__, "__models__", {})
                if name in models:
                    return list(getattr(backend, models[name])())
