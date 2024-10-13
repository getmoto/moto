import boto3
import pytest

from moto import mock_aws
from moto.utilities.id_generator import ResourceIdentifier, moto_id_manager


@pytest.fixture(scope="function")
def account_id():
    """Return the current Account ID. Will reach out to AWS if so configured."""
    from . import allow_aws_request

    if allow_aws_request():
        identity = boto3.client("sts", "us-east-1").get_caller_identity()
        yield identity["Account"]
    else:
        with mock_aws():
            identity = boto3.client("sts", "us-east-1").get_caller_identity()
            yield identity["Account"]


@pytest.fixture
def set_custom_id():
    set_ids = []

    def _set_custom_id(resource_identifier: ResourceIdentifier, custom_id):
        moto_id_manager.set_custom_id(
            resource_identifier=resource_identifier, custom_id=custom_id
        )
        set_ids.append(resource_identifier)

    yield _set_custom_id

    for resource_identifier in set_ids:
        moto_id_manager.unset_custom_id(resource_identifier)
