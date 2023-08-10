from moto.utilities.distutils_version import LooseVersion

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version


RESPONSES_VERSION = version("responses")
WERKZEUG_VERSION = version("werkzeug")


def is_responses_0_17_x() -> bool:
    return LooseVersion(RESPONSES_VERSION) >= LooseVersion("0.17.0")


def is_werkzeug_2_3_x() -> bool:
    return LooseVersion(WERKZEUG_VERSION) >= LooseVersion("2.3.0")
