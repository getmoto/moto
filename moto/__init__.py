import os

__title__ = "moto"
__version__ = "5.1.15.dev"

MOTO_ROOT = os.path.dirname(os.path.abspath(__file__))

from moto.core.decorator import mock_aws as mock_aws  # noqa: E402
