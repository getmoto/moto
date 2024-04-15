import requests

from moto import mock_aws, settings
from moto.awslambda.models import LambdaBackend
from moto.awslambda.utils import get_backend
from moto.awslambda_simple.models import LambdaSimpleBackend
from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.config import default_user_config


@mock_aws
def test_change_configuration_using_api() -> None:
    assert default_user_config["batch"] == {"use_docker": True}
    assert default_user_config["lambda"] == {"use_docker": True}

    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
    )
    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": True}
    assert resp.json()["lambda"] == {"use_docker": True}

    # Update a single configuration item
    requests.post(
        f"http://{base_url}/moto-api/config", json={"batch": {"use_docker": False}}
    )

    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": False}
    assert resp.json()["lambda"] == {"use_docker": True}

    if settings.TEST_DECORATOR_MODE:
        isinstance(get_backend(DEFAULT_ACCOUNT_ID, "us-east-1"), LambdaBackend)

    # Update multiple configuration items
    requests.post(
        f"http://{base_url}/moto-api/config",
        json={"batch": {"use_docker": True}, "lambda": {"use_docker": False}},
    )

    resp = requests.get(f"http://{base_url}/moto-api/config")
    assert resp.json()["batch"] == {"use_docker": True}
    assert resp.json()["lambda"] == {"use_docker": False}

    if settings.TEST_DECORATOR_MODE:
        isinstance(get_backend(DEFAULT_ACCOUNT_ID, "us-east-1"), LambdaSimpleBackend)

    # reset
    requests.post(
        f"http://{base_url}/moto-api/config",
        json={"batch": {"use_docker": True}, "lambda": {"use_docker": True}},
    )
