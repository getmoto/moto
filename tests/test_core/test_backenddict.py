import random
import time
import pytest

from moto.core import BaseBackend, BackendDict, DEFAULT_ACCOUNT_ID
from moto.core.base_backend import AccountSpecificBackend

from moto.autoscaling.models import AutoScalingBackend
from moto.ec2.models import EC2Backend
from moto.elbv2.models import ELBv2Backend

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

    def setup_method(self):
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
    for backend in [ExampleBackend, set, list, BaseBackend]:
        hashes.append(BackendDict(backend, "n/a").__hash__())
    # Hash is different for different backends
    set(hashes).should.have.length_of(4)


def test_account_specific_dict_can_be_hashed():
    hashes = []
    ids = ["01234567912", "01234567911", "01234567913", "000000000000", "0"]
    for accnt_id in ids:
        asb = _create_asb(accnt_id)
        hashes.append(asb.__hash__())
    # Hash is different for different accounts
    set(hashes).should.have.length_of(5)


def _create_asb(account_id, backend=None, use_boto3_regions=False, regions=None):
    return AccountSpecificBackend(
        service_name="ec2",
        account_id=account_id,
        backend=backend or ExampleBackend,
        use_boto3_regions=use_boto3_regions,
        additional_regions=regions,
    )


def test_multiple_backends_cache_behaviour():

    ec2 = BackendDict(EC2Backend, "ec2")
    ec2_useast1 = ec2[DEFAULT_ACCOUNT_ID]["us-east-1"]
    assert type(ec2_useast1) == EC2Backend

    autoscaling = BackendDict(AutoScalingBackend, "autoscaling")
    as_1 = autoscaling[DEFAULT_ACCOUNT_ID]["us-east-1"]
    assert type(as_1) == AutoScalingBackend

    from moto.elbv2 import elbv2_backends

    elbv2_useast = elbv2_backends["00000000"]["us-east-1"]
    assert type(elbv2_useast) == ELBv2Backend
    elbv2_useast2 = elbv2_backends[DEFAULT_ACCOUNT_ID]["us-east-2"]
    assert type(elbv2_useast2) == ELBv2Backend

    ec2_useast1 = ec2[DEFAULT_ACCOUNT_ID]["us-east-1"]
    assert type(ec2_useast1) == EC2Backend
    ec2_useast2 = ec2[DEFAULT_ACCOUNT_ID]["us-east-2"]
    assert type(ec2_useast2) == EC2Backend

    as_1 = autoscaling[DEFAULT_ACCOUNT_ID]["us-east-1"]
    assert type(as_1) == AutoScalingBackend


def test_backenddict_cache_hits_and_misses():
    backend = BackendDict(ExampleBackend, "ebs")
    backend.__getitem__.cache_clear()

    assert backend.__getitem__.cache_info().hits == 0
    assert backend.__getitem__.cache_info().misses == 0
    assert backend.__getitem__.cache_info().currsize == 0

    # Create + Retrieve an account - verify it is stored in cache
    accnt_1 = backend["accnt1"]
    assert accnt_1.account_id == "accnt1"

    assert backend.__getitem__.cache_info().hits == 0
    assert backend.__getitem__.cache_info().misses == 1
    assert backend.__getitem__.cache_info().currsize == 1

    # Creating + Retrieving a second account
    accnt_2 = backend["accnt2"]
    assert accnt_2.account_id == "accnt2"

    assert backend.__getitem__.cache_info().hits == 0
    assert backend.__getitem__.cache_info().misses == 2
    assert backend.__getitem__.cache_info().currsize == 2

    # Retrieving the first account from cache
    accnt_1_again = backend["accnt1"]
    assert accnt_1_again.account_id == "accnt1"

    assert backend.__getitem__.cache_info().hits == 1
    assert backend.__getitem__.cache_info().misses == 2
    assert backend.__getitem__.cache_info().currsize == 2

    # Retrieving the second account from cache
    accnt_2_again = backend["accnt2"]
    assert accnt_2_again.account_id == "accnt2"

    assert backend.__getitem__.cache_info().hits == 2
    assert backend.__getitem__.cache_info().misses == 2
    assert backend.__getitem__.cache_info().currsize == 2


def test_asb_cache_hits_and_misses():
    backend = BackendDict(ExampleBackend, "ebs")
    acb = backend["accnt_id"]
    acb.__getitem__.cache_clear()

    assert acb.__getitem__.cache_info().hits == 0
    assert acb.__getitem__.cache_info().misses == 0
    assert acb.__getitem__.cache_info().currsize == 0

    # Create + Retrieve an account - verify it is stored in cache
    region_1 = acb["us-east-1"]
    assert region_1.region_name == "us-east-1"

    assert acb.__getitem__.cache_info().hits == 0
    assert acb.__getitem__.cache_info().misses == 1
    assert acb.__getitem__.cache_info().currsize == 1

    # Creating + Retrieving a second account
    region_2 = acb["us-east-2"]
    assert region_2.region_name == "us-east-2"

    assert acb.__getitem__.cache_info().hits == 0
    assert acb.__getitem__.cache_info().misses == 2
    assert acb.__getitem__.cache_info().currsize == 2

    # Retrieving the first account from cache
    region_1_again = acb["us-east-1"]
    assert region_1_again.region_name == "us-east-1"

    assert acb.__getitem__.cache_info().hits == 1
    assert acb.__getitem__.cache_info().misses == 2
    assert acb.__getitem__.cache_info().currsize == 2

    # Retrieving the second account from cache
    region_2_again = acb["us-east-2"]
    assert region_2_again.region_name == "us-east-2"

    assert acb.__getitem__.cache_info().hits == 2
    assert acb.__getitem__.cache_info().misses == 2
    assert acb.__getitem__.cache_info().currsize == 2
