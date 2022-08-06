import random
import time
import pytest

from moto.core import BaseBackend
from moto.core.utils import AccountSpecificBackend, BackendDict
from threading import Thread


class ExampleBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)


def test_backend_dict_returns_nothing_by_default():
    backend_dict = BackendDict(ExampleBackend, "ebs")
    list(backend_dict.items()).should.equal([])


def test_account_specific_dict_contains_known_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict["account"].should.have.key("eu-north-1")
    backend_dict["account"]["eu-north-1"].should.be.a(ExampleBackend)


def test_backend_dict_known_regions_can_be_retrieved_directly():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict["account"]["eu-west-1"].should.be.a(ExampleBackend)


def test_backend_dict_can_get_known_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")["12345"]
    backend_dict["us-east-1"].should.be.a(ExampleBackend)


def test_backend_dict_does_not_contain_unknown_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    backend_dict["account"].shouldnt.have.key("mars-south-1")


def test_backend_dict_fails_when_retrieving_unknown_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2")
    with pytest.raises(KeyError):
        backend_dict["account"]["mars-south-1"]  # pylint: disable=pointless-statement


def test_backend_dict_can_retrieve_for_specific_account():
    backend_dict = BackendDict(ExampleBackend, "ec2")

    # Random account does not exist
    backend_dict.shouldnt.have.key("000000")

    # Retrieve AccountSpecificBackend by assuming it exists
    backend = backend_dict["012345"]
    backend.should.be.a(AccountSpecificBackend)

    backend.should.have.key("eu-north-1")
    regional_backend = backend["eu-north-1"]
    regional_backend.should.be.a(ExampleBackend)
    regional_backend.region_name.should.equal("eu-north-1")
    # We always return a fixed account_id for now, until we have proper multi-account support
    regional_backend.account_id.should.equal("012345")


def test_backend_dict_can_ignore_boto3_regions():
    backend_dict = BackendDict(ExampleBackend, "ec2", use_boto3_regions=False)
    backend_dict["account"].get("us-east-1").should.equal(None)


def test_backend_dict_can_specify_additional_regions():
    backend_dict = BackendDict(
        ExampleBackend, "ec2", additional_regions=["region1", "global"]
    )["123456"]
    backend_dict["us-east-1"].should.be.a(ExampleBackend)
    backend_dict["region1"].should.be.a(ExampleBackend)
    backend_dict["global"].should.be.a(ExampleBackend)

    # Unknown regions still do not exist
    backend_dict.get("us-east-3").should.equal(None)


class TestMultiThreadedAccess:
    class SlowExampleBackend(BaseBackend):
        def __init__(self, region_name, account_id):
            super().__init__(region_name, account_id)
            time.sleep(0.1)
            self.data = []

    def setup(self):
        self.backend = BackendDict(TestMultiThreadedAccess.SlowExampleBackend, "ec2")

    def test_access_a_slow_backend_concurrently(self):
        """None
        Usecase that we want to avoid:

        Thread 1 comes in, and sees the backend does not exist for this region
        Thread 1 starts creating the backend
        Thread 2 comes in, and sees the backend does not exist for this region
        Thread 2 starts creating the backend
        Thread 1 finishes creating the backend, initializes the list and adds a new value to it
        Thread 2 finishes creating the backend, re-initializes the list and adds a new value to it

        Creating the Backend for a region should only be invoked once at a time, and the execution flow should look like:

        Thread 1 comes in, and sees the backend does not exist for this region
        Thread 1 starts creating the backend
        Thread 2 comes in and is blocked
        Thread 1 finishes creating the backend, initializes the list and adds a new value to it
        Thread 2 gains access, and re-uses the created backend
        Thread 2 adds a new value to the list
        """

        def access(random_number):
            self.backend["123456789012"]["us-east-1"].data.append(random_number)

        threads = []

        for _ in range(0, 15):
            x = Thread(target=access, args=(random.randint(100, 200),))
            x.start()
            threads.append(x)

        for x in threads:
            x.join()

        self.backend["123456789012"]["us-east-1"].data.should.have.length_of(15)


def test_backend_dict_can_be_hashed():
    hashes = []
    for service in ["ec2", "iam", "kms", "redshift"]:
        hashes.append(BackendDict(None, service).__hash__())
    # Hash is different for different service names
    set(hashes).should.have.length_of(4)


@pytest.mark.parametrize(
    "service1,service2,eq",
    [("acm", "apm", False), ("acm", "acm", True), ("acm", "ec2", False)],
)
def test_multiple_backend_dicts_are_not_equal(service1, service2, eq):
    if eq:
        assert BackendDict(None, service1) == BackendDict(None, service2)
    else:
        assert BackendDict(None, service1) != BackendDict(None, service2)


def test_multiple_account_specific_dicts_are_equal():
    asb1a = _create_asb("ec2", "01234567912")
    asb1b = _create_asb("ec2", "01234567912", use_boto3_regions=True)
    asb1c = _create_asb("ec2", "01234567912", regions=["sth"])
    asb1d = _create_asb("ec2", "01234567912", use_boto3_regions=True, regions=["sth"])

    assert asb1a == asb1b
    assert asb1a == asb1c
    assert asb1a == asb1d

    asb2 = _create_asb("iam", "01234567912")
    assert asb1a != asb2

    asb3 = _create_asb("iam", "0123450000")
    assert asb1a != asb3
    assert asb2 != asb3


def test_account_specific_dict_can_be_hashed():
    hashes = []
    for service in ["ec2", "iam", "kms", "redshift"]:
        ids = ["01234567912", "01234567911", "01234567913", "000000000000", "0"]
        for accnt_id in ids:
            asb = _create_asb(service, accnt_id)
            hashes.append(asb.__hash__())
    # Hash is different for different service names + accounts
    set(hashes).should.have.length_of(20)


def _create_asb(service_name, account_id, use_boto3_regions=False, regions=None):
    return AccountSpecificBackend(
        service_name,
        account_id,
        backend=None,
        use_boto3_regions=use_boto3_regions,
        additional_regions=regions,
    )
