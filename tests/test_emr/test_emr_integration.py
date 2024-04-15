import boto3
import pytest

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.ec2 import ec2_backends
from moto.emr.utils import EmrSecurityGroupManager

ec2_backend = ec2_backends[ACCOUNT_ID]["us-east-1"]


@mock_aws
def test_default_emr_security_groups_get_created_on_first_job_flow():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-east-1a"
    )

    def _get_default_security_groups():
        group_resp = ec2_client.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc.id]},
                {
                    "Name": "group-name",
                    "Values": [
                        "ElasticMapReduce-Master-Private",
                        "ElasticMapReduce-Slave-Private",
                        "ElasticMapReduce-ServiceAccess",
                    ],
                },
            ]
        )
        return group_resp.get("SecurityGroups", [])

    assert len(_get_default_security_groups()) == 0

    client = boto3.client("emr", region_name="us-east-1")
    run_job_flow_params = dict(
        ReleaseLabel="emr-5.29.0",
        Instances={
            "KeepJobFlowAliveWhenNoSteps": True,
            "Ec2SubnetId": subnet.id,
            "InstanceGroups": [
                {
                    "Name": "Master",
                    "Market": "ON_DEMAND",
                    "InstanceRole": "MASTER",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 3,
                },
                {
                    "Name": "Core",
                    "Market": "ON_DEMAND",
                    "InstanceRole": "CORE",
                    "InstanceType": "m5.xlarge",
                    "InstanceCount": 2,
                },
            ],
        },
        JobFlowRole="EMR_EC2_DefaultRole",
        Name="test-emr-cluster-security-groups",
        ServiceRole="EMR_DefaultRole",
        VisibleToAllUsers=True,
    )
    cluster_id = client.run_job_flow(**run_job_flow_params)["JobFlowId"]

    # Default security groups should have been created.
    default_security_groups = _get_default_security_groups()
    default_security_group_ids = [sg["GroupId"] for sg in default_security_groups]
    assert len(default_security_group_ids) == 3

    resp = client.describe_cluster(ClusterId=cluster_id)
    ec2_attrs = resp["Cluster"]["Ec2InstanceAttributes"]
    assert ec2_attrs["Ec2SubnetId"] == subnet.id
    cluster_security_group_ids = [
        ec2_attrs["EmrManagedMasterSecurityGroup"],
        ec2_attrs["EmrManagedSlaveSecurityGroup"],
        ec2_attrs["ServiceAccessSecurityGroup"],
    ]
    assert set(cluster_security_group_ids) == set(default_security_group_ids)


@pytest.mark.skipif(
    settings.TEST_SERVER_MODE, reason="Can't modify backend directly in server mode."
)
class TestEmrSecurityGroupManager:
    mocks = []

    def setup_method(self):
        self.mock = mock_aws()
        self.mock.start()
        ec2_client = boto3.client("ec2", region_name="us-east-1")
        ec2 = boto3.resource("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        self.vpc_id = vpc.id
        self.ec2 = ec2
        self.ec2_client = ec2_client

    def teardown_method(self):
        self.mock.stop()

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
        manager = EmrSecurityGroupManager(
            ec2_backends[ACCOUNT_ID]["us-east-1"], self.vpc_id
        )
        assert len(self._default_emr_security_groups()) == 0
        manager.manage_security_groups(None, None, None)
        assert len(self._default_emr_security_groups()) == 3

    def test_emr_security_groups_do_not_get_created_if_already_exist(self):
        manager = EmrSecurityGroupManager(
            ec2_backends[ACCOUNT_ID]["us-east-1"], self.vpc_id
        )
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
        manager = EmrSecurityGroupManager(
            ec2_backends[ACCOUNT_ID]["us-east-1"], self.vpc_id
        )
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
        manager = EmrSecurityGroupManager(
            ec2_backends[ACCOUNT_ID]["us-east-1"], self.vpc_id
        )
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
        manager = EmrSecurityGroupManager(
            ec2_backends[ACCOUNT_ID]["us-east-1"], self.vpc_id
        )
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
