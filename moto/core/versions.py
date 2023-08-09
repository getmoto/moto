from moto.utilities.distutils_version import LooseVersion

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version


WERKZEUG_VERSION = version("werkzeug")


def is_werkzeug_2_3_x() -> bool:
    return LooseVersion(WERKZEUG_VERSION) >= LooseVersion("2.3.0")
