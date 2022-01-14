import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_elbv2, mock_ec2
from moto.core import ACCOUNT_ID

from .test_elbv2 import create_load_balancer


@mock_ec2
@mock_elbv2
def test_create_target_group_with_invalid_healthcheck_protocol():
    _, vpc, _, _, _, conn = create_load_balancer()
    # Can't create a target group with an invalid protocol
    with pytest.raises(ClientError) as exc:
        conn.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="/HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "Value /HTTP at 'healthCheckProtocol' failed to satisfy constraint: Member must satisfy enum value set: ['HTTPS', 'HTTP', 'TCP']"
    )


@mock_elbv2
@mock_ec2
def test_create_target_group_and_listeners():
    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]
    target_group_arn = target_group["TargetGroupArn"]

    # Add tags to the target group
    conn.add_tags(
        ResourceArns=[target_group_arn], Tags=[{"Key": "target", "Value": "group"}]
    )
    conn.describe_tags(ResourceArns=[target_group_arn])["TagDescriptions"][0][
        "Tags"
    ].should.equal([{"Key": "target", "Value": "group"}])

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {"Type": "forward", "TargetGroupArn": target_group.get("TargetGroupArn")}
        ],
    )
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(80)
    listener.get("Protocol").should.equal("HTTP")
    listener.get("DefaultActions").should.equal(
        [{"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}]
    )
    http_listener_arn = listener.get("ListenerArn")

    response = conn.describe_target_groups(
        LoadBalancerArn=load_balancer_arn, Names=["a-target"]
    )
    response.get("TargetGroups").should.have.length_of(1)

    # And another with SSL
    actions = {"Type": "forward", "TargetGroupArn": target_group.get("TargetGroupArn")}
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[
            {
                "CertificateArn": "arn:aws:iam:{}:server-certificate/test-cert".format(
                    ACCOUNT_ID
                )
            }
        ],
        DefaultActions=[actions],
    )
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(443)
    listener.get("Protocol").should.equal("HTTPS")
    listener.get("Certificates").should.equal(
        [
            {
                "CertificateArn": "arn:aws:iam:{}:server-certificate/test-cert".format(
                    ACCOUNT_ID
                )
            }
        ]
    )
    listener.get("DefaultActions").should.equal(
        [{"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}]
    )

    https_listener_arn = listener.get("ListenerArn")

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(2)
    response = conn.describe_listeners(ListenerArns=[https_listener_arn])
    response.get("Listeners").should.have.length_of(1)
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(443)
    listener.get("Protocol").should.equal("HTTPS")

    response = conn.describe_listeners(
        ListenerArns=[http_listener_arn, https_listener_arn]
    )
    response.get("Listeners").should.have.length_of(2)

    conn.create_rule(
        ListenerArn=http_listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]},],
        Priority=3,
        Actions=[actions],
    )
    # Try to delete the target group and it fails because there's a
    # listener referencing it
    with pytest.raises(ClientError) as e:
        conn.delete_target_group(TargetGroupArn=target_group.get("TargetGroupArn"))
    e.value.operation_name.should.equal("DeleteTargetGroup")
    e.value.args.should.equal(
        (
            "An error occurred (ResourceInUse) when calling the DeleteTargetGroup operation: The target group 'arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/a-target/50dc6c495c0c9188' is currently in use by a listener or a rule",
        )
    )  # NOQA

    # Delete one listener
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(2)
    conn.delete_listener(ListenerArn=http_listener_arn)
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(1)

    # Then delete the load balancer
    conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)

    # It's gone
    response = conn.describe_load_balancers()
    response.get("LoadBalancers").should.have.length_of(0)

    # And it deleted the remaining listener
    with pytest.raises(ClientError) as e:
        conn.describe_listeners(ListenerArns=[http_listener_arn, https_listener_arn])
    e.value.response["Error"]["Code"].should.equal("ListenerNotFound")

    # But not the target groups
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)

    # Which we'll now delete
    conn.delete_target_group(TargetGroupArn=target_group.get("TargetGroupArn"))
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(0)


@mock_elbv2
@mock_ec2
def test_create_target_group_without_non_required_parameters():
    response, vpc, _, _, _, conn = create_load_balancer()

    # request without HealthCheckIntervalSeconds parameter
    # which is default to 30 seconds
    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
    )
    response.get("TargetGroups", []).should.have.length_of(1)


@mock_elbv2
@mock_ec2
def test_create_invalid_target_group_long_name():
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Fail to create target group with name which length is 33
    long_name = "A" * 33
    with pytest.raises(ClientError) as exc:
        conn.create_target_group(
            Name=long_name,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "Target group name 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' cannot be longer than '32' characters"
    )


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("name", ["-name", "name-", "-name-", "Na--me"])
def test_create_invalid_target_group_invalid_characters(name):
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    with pytest.raises(ClientError) as exc:
        conn.create_target_group(
            Name=name,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'targetGroup.targetGroupArn.targetGroupName' failed to satisfy constraint: Member must satisfy regular expression pattern: (?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$"
    )


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("name", ["example.com", "test@test"])
def test_create_invalid_target_group_alphanumeric_characters(name):
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    with pytest.raises(ClientError) as exc:
        conn.create_target_group(
            Name=name,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        f"Target group name '{name}' can only contain characters that are alphanumeric characters or hyphens(-)"
    )


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("name", ["name", "Name", "000"])
def test_create_valid_target_group_valid_names(name):
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    conn.create_target_group(
        Name=name,
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )


@mock_ec2
@mock_elbv2
def test_target_group_attributes():
    response, vpc, _, _, _, conn = create_load_balancer()

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)
    target_group_arn = target_group["TargetGroupArn"]

    # check if Names filter works
    response = conn.describe_target_groups(Names=[])
    response = conn.describe_target_groups(Names=["a-target"])
    response.get("TargetGroups").should.have.length_of(1)
    target_group_arn = target_group["TargetGroupArn"]

    # The attributes should start with the two defaults
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response["Attributes"].should.have.length_of(2)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["deregistration_delay.timeout_seconds"].should.equal("300")
    attributes["stickiness.enabled"].should.equal("false")

    # Add cookie stickiness
    response = conn.modify_target_group_attributes(
        TargetGroupArn=target_group_arn,
        Attributes=[
            {"Key": "stickiness.enabled", "Value": "true"},
            {"Key": "stickiness.type", "Value": "lb_cookie"},
        ],
    )

    # The response should have only the keys updated
    response["Attributes"].should.have.length_of(2)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["stickiness.type"].should.equal("lb_cookie")
    attributes["stickiness.enabled"].should.equal("true")

    # These new values should be in the full attribute list
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response["Attributes"].should.have.length_of(3)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["stickiness.type"].should.equal("lb_cookie")
    attributes["stickiness.enabled"].should.equal("true")


@mock_elbv2
@mock_ec2
def test_create_target_group_invalid_protocol():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Can't create a target group with an invalid protocol
    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="/HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.contain(
        "Value /HTTP at 'healthCheckProtocol' failed to satisfy constraint"
    )


@mock_elbv2
def test_describe_invalid_target_group():
    conn = boto3.client("elbv2", region_name="us-east-1")

    # Check error raises correctly
    with pytest.raises(ClientError) as exc:
        conn.describe_target_groups(Names=["invalid"])
    err = exc.value.response["Error"]
    err["Code"].should.equal("TargetGroupNotFound")
    err["Message"].should.equal("The specified target group does not exist.")


@mock_elbv2
@mock_ec2
def test_describe_target_groups_no_arguments():
    response, vpc, _, _, _, conn = create_load_balancer()

    response.get("LoadBalancers")[0].get("LoadBalancerArn")

    conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "201"},
    )

    groups = conn.describe_target_groups()["TargetGroups"]
    groups.should.have.length_of(1)
    groups[0].should.have.key("Matcher").equals({"HttpCode": "201"})


@mock_elbv2
@mock_ec2
def test_modify_target_group():
    client = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    response = client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    arn = response.get("TargetGroups")[0]["TargetGroupArn"]

    client.modify_target_group(
        TargetGroupArn=arn,
        HealthCheckProtocol="HTTPS",
        HealthCheckPort="8081",
        HealthCheckPath="/status",
        HealthCheckIntervalSeconds=10,
        HealthCheckTimeoutSeconds=10,
        HealthyThresholdCount=10,
        UnhealthyThresholdCount=4,
        Matcher={"HttpCode": "200-399"},
    )

    response = client.describe_target_groups(TargetGroupArns=[arn])
    response["TargetGroups"][0]["Matcher"]["HttpCode"].should.equal("200-399")
    response["TargetGroups"][0]["HealthCheckIntervalSeconds"].should.equal(10)
    response["TargetGroups"][0]["HealthCheckPath"].should.equal("/status")
    response["TargetGroups"][0]["HealthCheckPort"].should.equal("8081")
    response["TargetGroups"][0]["HealthCheckProtocol"].should.equal("HTTPS")
    response["TargetGroups"][0]["HealthCheckTimeoutSeconds"].should.equal(10)
    response["TargetGroups"][0]["HealthyThresholdCount"].should.equal(10)
    response["TargetGroups"][0]["UnhealthyThresholdCount"].should.equal(4)


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("target_type", ["instance", "ip", "lambda", "alb", "other"])
def test_create_target_group_with_target_type(target_type):
    response, _, _, _, _, conn = create_load_balancer()

    response = conn.create_target_group(Name="a-target", TargetType=target_type)

    group = response["TargetGroups"][0]
    group.should.have.key("TargetGroupArn")
    group.should.have.key("TargetGroupName").equal("a-target")
    group.should.have.key("TargetType").equal(target_type)
    group.shouldnt.have.key("Protocol")
    group.shouldnt.have.key("VpcId")

    group = conn.describe_target_groups()["TargetGroups"][0]
    group.should.have.key("TargetGroupArn")
    group.should.have.key("TargetGroupName").equal("a-target")
    group.should.have.key("TargetType").equal(target_type)
    group.shouldnt.have.key("Protocol")
    group.shouldnt.have.key("VpcId")


@mock_elbv2
@mock_ec2
def test_delete_target_group_after_modifying_listener():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id,
    )
    target_group_arn1 = response.get("TargetGroups")[0]["TargetGroupArn"]

    response = client.create_target_group(
        Name="a-target-2", Protocol="HTTPS", Port=8081, VpcId=vpc.id,
    )
    target_group_arn2 = response.get("TargetGroups")[0]["TargetGroupArn"]

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn1}],
    )
    listener_arn = response["Listeners"][0].get("ListenerArn")

    client.modify_listener(
        ListenerArn=listener_arn,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn2,}],
    )

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    default_actions = response["Listeners"][0]["DefaultActions"]
    default_actions.should.equal(
        [{"Type": "forward", "TargetGroupArn": target_group_arn2}]
    )

    # Target Group 1 can now be deleted, as the LB points to group 2
    client.delete_target_group(TargetGroupArn=target_group_arn1)

    # Sanity check - we're still pointing to group 2
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    default_actions = response["Listeners"][0]["DefaultActions"]
    default_actions.should.equal(
        [{"Type": "forward", "TargetGroupArn": target_group_arn2}]
    )


@mock_elbv2
@mock_ec2
def test_create_listener_with_multiple_target_groups():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id,
    )
    target_group_arn1 = response.get("TargetGroups")[0]["TargetGroupArn"]

    response = client.create_target_group(
        Name="a-target-2", Protocol="HTTPS", Port=8081, VpcId=vpc.id,
    )
    target_group_arn2 = response.get("TargetGroups")[0]["TargetGroupArn"]

    conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {
                "Type": "forward",
                "ForwardConfig": {
                    "TargetGroups": [
                        {"TargetGroupArn": target_group_arn1, "Weight": 100},
                        {"TargetGroupArn": target_group_arn2, "Weight": 0},
                    ],
                    "TargetGroupStickinessConfig": {
                        "Enabled": False,
                        "DurationSeconds": 300,
                    },
                },
            }
        ],
    )

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    listener = response["Listeners"][0]
    groups = listener["DefaultActions"][0]["ForwardConfig"]["TargetGroups"]
    groups.should.have.length_of(2)
    groups.should.contain({"TargetGroupArn": target_group_arn1, "Weight": 100})
    groups.should.contain({"TargetGroupArn": target_group_arn2, "Weight": 0})


@mock_elbv2
@mock_ec2
def test_create_listener_with_invalid_target_group():
    response, _, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    with pytest.raises(ClientError) as exc:
        conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[
                {
                    "Type": "forward",
                    "ForwardConfig": {
                        "TargetGroups": [{"TargetGroupArn": "unknown", "Weight": 100}]
                    },
                }
            ],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("TargetGroupNotFound")
    err["Message"].should.equal("Target group 'unknown' not found")


@mock_elbv2
@mock_ec2
def test_delete_target_group_while_listener_still_exists():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id,
    )
    target_group_arn1 = response.get("TargetGroups")[0]["TargetGroupArn"]

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {
                "Type": "forward",
                "ForwardConfig": {
                    "TargetGroups": [
                        {"TargetGroupArn": target_group_arn1, "Weight": 100}
                    ]
                },
            }
        ],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    # Deletion does not succeed if the Listener still exists
    with pytest.raises(ClientError) as exc:
        client.delete_target_group(TargetGroupArn=target_group_arn1)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceInUse")
    err["Message"].should.equal(
        f"The target group '{target_group_arn1}' is currently in use by a listener or a rule"
    )

    client.delete_listener(ListenerArn=listener_arn)

    # Deletion does succeed now that the listener is deleted
    client.delete_target_group(TargetGroupArn=target_group_arn1)
