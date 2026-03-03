import pytest

from moto.core.errors import get_error_model
from moto.core.utils import get_service_model


def test_exception_not_modeled_warning() -> None:
    class UnmodeledException(Exception):
        pass

    service_model = get_service_model("rds")
    with pytest.warns(UserWarning, match="does not match an error shape"):
        get_error_model(UnmodeledException(), service_model)
