import random
import time
from threading import Thread
from typing import Any, List, Optional

import pytest

from moto.autoscaling.models import AutoScalingBackend
from moto.core import DEFAULT_ACCOUNT_ID
from moto.core.base_backend import AccountSpecificBackend, BackendDict, BaseBackend
from moto.ec2.models import EC2Backend
from moto.elbv2.models import ELBv2Backend
from moto.utilities.utils import PARTITION_NAMES


class ExampleBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)


def test_backend_dict_returns_nothing_by_default() -> None:
    backend_dict = BackendDict(ExampleBackend, "ebs")
    assert list(backend_dict.items()) == []


def test_account_specific_dict_contains_known_regions() -> None:
    backend_dict = BackendDict(ExampleBackend, "ec2")
    assert isinstance(backend_dict["account"]["eu-north-1"], ExampleBackend)


def test_backend_dict_does_not_contain_unknown_regions() -> None:
    backend_dict = BackendDict(ExampleBackend, "ec2")
    assert "mars-south-1" not in backend_dict["account"]


def test_backend_dict_fails_when_retrieving_unknown_regions() -> None:
    backend_dict = BackendDict(ExampleBackend, "ec2")
    with pytest.raises(KeyError):
        backend_dict["account"]["mars-south-1"]  # pylint: disable=pointless-statement


def test_backend_dict_can_retrieve_for_specific_account() -> None:
    backend_dict = BackendDict(ExampleBackend, "ec2")

    # Random account does not exist
    assert "000000" not in backend_dict

    # Retrieve AccountSpecificBackend by assuming it exists
    backend = backend_dict["012345"]
    assert isinstance(backend, AccountSpecificBackend)

    assert "eu-north-1" in backend
    regional_backend = backend["eu-north-1"]
    assert isinstance(regional_backend, ExampleBackend)
    assert regional_backend.region_name == "eu-north-1"
    # We always return a fixed account_id for now, until we have proper multi-account support
    assert regional_backend.account_id == "012345"


def test_backend_dict_can_ignore_boto3_regions() -> None:
    backend_dict = BackendDict(ExampleBackend, "ec2", use_boto3_regions=False)
    assert backend_dict["account"].get("us-east-1") is None


def test_backend_dict_can_specify_additional_regions() -> None:
    backend_dict = BackendDict(
        ExampleBackend, "ec2", additional_regions=["region1", "global", "aws"]
    )["123456"]
    assert isinstance(backend_dict["us-east-1"], ExampleBackend)
    assert isinstance(backend_dict["region1"], ExampleBackend)
    assert isinstance(backend_dict["global"], ExampleBackend)

    # Unknown regions still do not exist
    assert backend_dict.get("us-east-3") is None


class TestMultiThreadedAccess:
    class SlowExampleBackend(BaseBackend):
        def __init__(self, region_name: str, account_id: str):
            super().__init__(region_name, account_id)
            time.sleep(0.1)
            self.data: List[int] = []

    def setup_method(self) -> None:
        self.backend = BackendDict(TestMultiThreadedAccess.SlowExampleBackend, "ec2")

    def test_access_a_slow_backend_concurrently(self) -> None:
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

        def access(random_number: int) -> None:
            self.backend["123456789012"]["us-east-1"].data.append(random_number)

        threads = []

        for _ in range(0, 15):
            x = Thread(target=access, args=(random.randint(100, 200),))
            x.start()
            threads.append(x)

        for x in threads:
            x.join()

        assert len(self.backend["123456789012"]["us-east-1"].data) == 15


def test_backend_dict_can_be_hashed() -> None:
    hashes = []
    for backend in [ExampleBackend, set, list, BaseBackend]:
        hashes.append(BackendDict(backend, "n/a").__hash__())
    # Hash is different for different backends
    assert len(set(hashes)) == 4


def test_account_specific_dict_can_be_hashed() -> None:
    hashes = []
    ids = ["01234567912", "01234567911", "01234567913", "000000000000", "0"]
    for accnt_id in ids:
        asb = _create_asb(accnt_id)
        hashes.append(asb.__hash__())
    # Hash is different for different accounts
    assert len(set(hashes)) == 5


def _create_asb(
    account_id: str,
    backend: Any = None,
    use_boto3_regions: bool = False,
    regions: Optional[List[str]] = None,
) -> Any:
    return AccountSpecificBackend(
        service_name="ec2",
        account_id=account_id,
        backend=backend or ExampleBackend,
        use_boto3_regions=use_boto3_regions,
        additional_regions=regions,
    )


def test_multiple_backends_cache_behaviour() -> None:
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


def test_global_region_defaults_to_aws() -> None:
    s3 = BackendDict(ExampleBackend, "s3", additional_regions=PARTITION_NAMES)

    # Internally we use 'aws' as the S3 region
    s3_aws = s3[DEFAULT_ACCOUNT_ID]["aws"]
    assert isinstance(s3_aws, ExampleBackend)

    # But users may still call this 'global'
    # Ensure that we're getting the backend
    s3_global = s3[DEFAULT_ACCOUNT_ID]["global"]
    assert s3_global == s3_aws

    # Changes to S3AWS should show up in global
    s3_aws.var = "test"  # type: ignore[attr-defined]
    assert s3_global.var == "test"  # type: ignore[attr-defined]

    assert "aws" in s3[DEFAULT_ACCOUNT_ID]
    assert "global" in s3[DEFAULT_ACCOUNT_ID]


def test_iterate_backend_dict() -> None:
    ec2 = BackendDict(EC2Backend, "ec2")
    _ = ec2[DEFAULT_ACCOUNT_ID]["us-east-1"]
    _ = ec2[DEFAULT_ACCOUNT_ID]["us-east-2"]

    regions = {"us-east-1", "us-east-2"}
    for account, region, backend in ec2.iter_backends():
        assert isinstance(backend, EC2Backend)
        assert region in regions
        regions.remove(region)
        assert account == DEFAULT_ACCOUNT_ID
