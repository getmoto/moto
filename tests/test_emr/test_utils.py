import boto3
import pytest

from moto import settings
from moto.ec2 import mock_ec2, ec2_backend
from moto.emr.utils import ReleaseLabel, EmrSecurityGroupManager


def test_invalid_release_labels_raise_exception():
    invalid_releases = [
        "",
        "0",
        "1.0",
        "emr-2.0",
    ]
    for invalid_release in invalid_releases:
        with pytest.raises(ValueError):
            ReleaseLabel(invalid_release)


def test_release_label_comparisons():
    assert str(ReleaseLabel("emr-5.1.2")) == "emr-5.1.2"

    assert ReleaseLabel("emr-5.0.0") != ReleaseLabel("emr-5.0.1")
    assert ReleaseLabel("emr-5.0.0") == ReleaseLabel("emr-5.0.0")

    assert ReleaseLabel("emr-5.31.0") > ReleaseLabel("emr-5.7.0")
    assert ReleaseLabel("emr-6.0.0") > ReleaseLabel("emr-5.7.0")

    assert ReleaseLabel("emr-5.7.0") < ReleaseLabel("emr-5.10.0")
    assert ReleaseLabel("emr-5.10.0") < ReleaseLabel("emr-5.10.1")

    assert ReleaseLabel("emr-5.60.0") >= ReleaseLabel("emr-5.7.0")
    assert ReleaseLabel("emr-6.0.0") >= ReleaseLabel("emr-6.0.0")

    assert ReleaseLabel("emr-5.7.0") <= ReleaseLabel("emr-5.17.0")
    assert ReleaseLabel("emr-5.7.0") <= ReleaseLabel("emr-5.7.0")

    releases_unsorted = [
        ReleaseLabel("emr-5.60.2"),
        ReleaseLabel("emr-4.0.1"),
        ReleaseLabel("emr-4.0.0"),
        ReleaseLabel("emr-5.7.3"),
    ]
    releases_sorted = [str(label) for label in sorted(releases_unsorted)]
    expected = [
        "emr-4.0.0",
        "emr-4.0.1",
        "emr-5.7.3",
        "emr-5.60.2",
    ]
    assert releases_sorted == expected


@pytest.mark.skipif(
    settings.TEST_SERVER_MODE, reason="Can't modify backend directly in server mode."
)
class TestEmrSecurityGroupManager(object):

    mocks = []

    def setup(self):
        self.mocks = [mock_ec2()]
        for mock in self.mocks:
            mock.start()
        ec2_client = boto3.client("ec2", region_name="us-east-1")
        ec2 = boto3.resource("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        self.vpc_id = vpc.id
        self.ec2 = ec2
        self.ec2_client = ec2_client

    def teardown(self):
        for mock in self.mocks:
            mock.stop()

    def _create_default_client_supplied_security_groups(self):
        master = self.ec2.create_security_group(
            GroupName="master", Description="master", VpcId=self.vpc_id
        )
        slave = self.ec2.create_security_group(
            GroupName="slave", Description="slave", VpcId=self.vpc_id
        )
        service = self.ec2.create_security_group(
            GroupName="service", Description="service", VpcId=self.vpc_id
        )
        return master, slave, service

    def _describe_security_groups(self, group_names):
        resp = self.ec2_client.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [self.vpc_id]},
                {"Name": "group-name", "Values": group_names},
            ]
        )
        return resp.get("SecurityGroups", [])

    def _default_emr_security_groups(self):
        group_names = [
            "ElasticMapReduce-Master-Private",
            "ElasticMapReduce-Slave-Private",
            "ElasticMapReduce-ServiceAccess",
        ]
        return self._describe_security_groups(group_names)

    def test_emr_security_groups_get_created_if_non_existent(self):
        manager = EmrSecurityGroupManager(ec2_backend, self.vpc_id)
        assert len(self._default_emr_security_groups()) == 0
        manager.manage_security_groups(None, None, None)
        assert len(self._default_emr_security_groups()) == 3

    def test_emr_security_groups_do_not_get_created_if_already_exist(self):
        manager = EmrSecurityGroupManager(ec2_backend, self.vpc_id)
        assert len(self._default_emr_security_groups()) == 0
        manager.manage_security_groups(None, None, None)
        emr_security_groups = self._default_emr_security_groups()
        assert len(emr_security_groups) == 3
        # Run again.  Group count should still be 3.
        emr_sg_ids_expected = [sg["GroupId"] for sg in emr_security_groups]
        manager.manage_security_groups(None, None, None)
        emr_security_groups = self._default_emr_security_groups()
        assert len(emr_security_groups) == 3
        emr_sg_ids_actual = [sg["GroupId"] for sg in emr_security_groups]
        assert emr_sg_ids_actual == emr_sg_ids_expected

    def test_emr_security_groups_do_not_get_created_if_client_supplied(self):
        (
            client_master,
            client_slave,
            client_service,
        ) = self._create_default_client_supplied_security_groups()
        manager = EmrSecurityGroupManager(ec2_backend, self.vpc_id)
        manager.manage_security_groups(
            client_master.id, client_slave.id, client_service.id
        )
        client_group_names = [
            client_master.group_name,
            client_slave.group_name,
            client_service.group_name,
        ]
        assert len(self._describe_security_groups(client_group_names)) == 3
        assert len(self._default_emr_security_groups()) == 0

    def test_client_supplied_invalid_security_group_identifier_raises_error(self):
        manager = EmrSecurityGroupManager(ec2_backend, self.vpc_id)
        args_bad = [
            ("sg-invalid", None, None),
            (None, "sg-invalid", None),
            (None, None, "sg-invalid"),
        ]
        for args in args_bad:
            with pytest.raises(ValueError) as exc:
                manager.manage_security_groups(*args)
            assert str(exc.value) == "The security group 'sg-invalid' does not exist"

    def test_client_supplied_security_groups_have_rules_added(self):
        (
            client_master,
            client_slave,
            client_service,
        ) = self._create_default_client_supplied_security_groups()
        manager = EmrSecurityGroupManager(ec2_backend, self.vpc_id)
        manager.manage_security_groups(
            client_master.id, client_slave.id, client_service.id
        )
        client_group_names = [
            client_master.group_name,
            client_slave.group_name,
            client_service.group_name,
        ]
        security_groups = self._describe_security_groups(client_group_names)
        for security_group in security_groups:
            assert len(security_group["IpPermissions"]) > 0
            assert len(security_group["IpPermissionsEgress"]) > 0
