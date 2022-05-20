import pytest

from moto.core import BaseBackend
from moto.core.utils import AccountSpecificBackend, BackendDict


class ExampleBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)


def test_backend_dict_returns_nothing_by_default():
    backend_dict = BackendDict(ExampleBackend, "ebs")
    backend_dict.should.equal({})


def test_backend_dict_contains_known_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict.should.have.key("eu-north-1")
    backend_dict["eu-north-1"].should.be.a(ExampleBackend)


def test_backend_dict_known_regions_can_be_retrieved_directly():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict["eu-west-1"].should.be.a(ExampleBackend)


def test_backend_dict_can_get_known_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict.get("us-east-1").should.be.a(ExampleBackend)


def test_backend_dict_does_not_contain_unknown_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict.shouldnt.have.key("mars-south-1")


def test_backend_dict_fails_when_retrieving_unknown_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    with pytest.raises(KeyError):
        backend_dict["mars-south-1"]  # pylint: disable=pointless-statement


def test_backend_dict_can_retrieve_for_specific_account():
    backend_dict = BackendDict(ExampleBackend, "ec2")

    # Retrieve AccountSpecificBackend after checking it exists
    backend_dict.should.have.key("000000")
    backend = backend_dict.get("000000")
    backend.should.be.a(AccountSpecificBackend)

    # Retrieve AccountSpecificBackend by assuming it exists
    backend = backend_dict["012345"]
    backend.should.be.a(AccountSpecificBackend)

    backend.should.have.key("eu-north-1")
    regional_backend = backend["eu-north-1"]
    regional_backend.should.be.a(ExampleBackend)
    regional_backend.region_name.should.equal("eu-north-1")
    # We always return a fixed account_id for now, until we have proper multi-account support
    regional_backend.account_id.should.equal("123456789012")


def test_backend_dict_can_ignore_boto3_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2", use_boto3_regions=False)
    backend_dict.get("us-east-1").should.equal(None)


def test_backend_dict_can_specify_additional_regions():
    backend_dict = BackendDict(
        ExampleBackend, "ec2", additional_regions=["region1", "global"]
    )
    backend_dict.get("us-east-1").should.be.a(ExampleBackend)
    backend_dict.get("region1").should.be.a(ExampleBackend)
    backend_dict.get("global").should.be.a(ExampleBackend)

    # Unknown regions still do not exist
    backend_dict.get("us-east-3").should.equal(None)
