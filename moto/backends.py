from __future__ import unicode_literals

import importlib
import moto


decorators = [
    d
    for d in dir(moto)
    if d.startswith("mock_") and not d.endswith("_deprecated") and not d == "mock_all"
]
decorator_functions = [getattr(moto, f) for f in decorators]
BACKENDS = {f.boto3_name: (f.name, f.backend) for f in decorator_functions}
BACKENDS["moto_api"] = ("core", "moto_api_backends")
BACKENDS["instance_metadata"] = ("instance_metadata", "instance_metadata_backends")
BACKENDS["s3bucket_path"] = ("s3", "s3_backends")

imported_backends = set()


def _import_backend(module_name, backends_name):
    module = importlib.import_module("moto." + module_name)
    return getattr(module, backends_name)


def backends():
    for module_name, backends_name in BACKENDS.values():
        yield _import_backend(module_name, backends_name)


def loaded_backends():
    for name in imported_backends:
        module_name, backends_name = BACKENDS[name]
        yield name, _import_backend(module_name, backends_name)


def get_backend(name):
    module_name, backends_name = BACKENDS[name]
    imported_backends.add(name)
    return _import_backend(module_name, backends_name)


def get_model(name, region_name):
    for backends_ in backends():
        for region, backend in backends_.items():
            if region == region_name:
                models = getattr(backend.__class__, "__models__", {})
                if name in models:
                    return list(getattr(backend, models[name])())
