import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_elbv2, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

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
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Value /HTTP at 'healthCheckProtocol' failed to satisfy constraint: Member must satisfy enum value set: ['HTTPS', 'HTTP', 'TCP', 'TLS', 'UDP', 'TCP_UDP', 'GENEVE']"
    )


@mock_elbv2
@mock_ec2
def test_create_target_group_with_tags():
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
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
        Tags=[{"Key": "key1", "Value": "val1"}],
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]

    # Add tags to the target group
    conn.add_tags(
        ResourceArns=[target_group_arn],
        Tags=[{"Key": "key2", "Value": "val2"}],
    )
    tags = conn.describe_tags(ResourceArns=[target_group_arn])["TagDescriptions"][0][
        "Tags"
    ]
    assert tags == [{"Key": "key1", "Value": "val1"}, {"Key": "key2", "Value": "val2"}]

    # Verify they can be removed
    conn.remove_tags(ResourceArns=[target_group_arn], TagKeys=["key1"])
    tags = conn.describe_tags(ResourceArns=[target_group_arn])["TagDescriptions"][0][
        "Tags"
    ]
    assert tags == [{"Key": "key2", "Value": "val2"}]


@mock_elbv2
@mock_ec2
def test_create_target_group_and_listeners():
    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]
    assert target_group["HealthCheckProtocol"] == "HTTP"

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    assert len(response["TargetGroups"]) == 1

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener = response["Listeners"][0]
    assert listener["Port"] == 80
    assert listener["Protocol"] == "HTTP"
    assert listener["DefaultActions"] == [
        {"TargetGroupArn": target_group_arn, "Type": "forward"}
    ]
    http_listener_arn = listener["ListenerArn"]

    response = conn.describe_target_groups(
        LoadBalancerArn=load_balancer_arn,
    )
    assert len(response["TargetGroups"]) == 1

    # And another with SSL
    actions = {"Type": "forward", "TargetGroupArn": target_group_arn}
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[
            {"CertificateArn": f"arn:aws:iam:{ACCOUNT_ID}:server-certificate/test-cert"}
        ],
        DefaultActions=[actions],
    )
    listener = response["Listeners"][0]
    assert listener["Port"] == 443
    assert listener["Protocol"] == "HTTPS"
    assert listener["Certificates"] == [
        {"CertificateArn": f"arn:aws:iam:{ACCOUNT_ID}:server-certificate/test-cert"}
    ]
    assert listener["DefaultActions"] == [
        {"TargetGroupArn": target_group_arn, "Type": "forward"}
    ]

    https_listener_arn = listener["ListenerArn"]

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    assert len(response["Listeners"]) == 2
    response = conn.describe_listeners(ListenerArns=[https_listener_arn])
    assert len(response["Listeners"]) == 1
    listener = response["Listeners"][0]
    assert listener["Port"] == 443
    assert listener["Protocol"] == "HTTPS"

    response = conn.describe_listeners(
        ListenerArns=[http_listener_arn, https_listener_arn]
    )
    assert len(response["Listeners"]) == 2

    conn.create_rule(
        ListenerArn=http_listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[actions],
    )
    # Try to delete the target group and it fails because there's a
    # listener referencing it
    with pytest.raises(ClientError) as e:
        conn.delete_target_group(TargetGroupArn=target_group_arn)
    assert e.value.operation_name == "DeleteTargetGroup"
    assert (
        e.value.response["Error"]["Message"]
        == f"The target group 'arn:aws:elasticloadbalancing:us-east-1:{ACCOUNT_ID}:targetgroup/a-target/50dc6c495c0c9188' is currently in use by a listener or a rule"
    )

    # Delete one listener
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    assert len(response["Listeners"]) == 2
    conn.delete_listener(ListenerArn=http_listener_arn)
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    assert len(response["Listeners"]) == 1

    # Then delete the load balancer
    conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)

    # It's gone
    response = conn.describe_load_balancers()
    assert len(response["LoadBalancers"]) == 0

    # And it deleted the remaining listener
    with pytest.raises(ClientError) as e:
        conn.describe_listeners(ListenerArns=[http_listener_arn, https_listener_arn])
    assert e.value.response["Error"]["Code"] == "ListenerNotFound"

    # But not the target groups
    response = conn.describe_target_groups()
    assert len(response["TargetGroups"]) == 1

    # Which we'll now delete
    conn.delete_target_group(TargetGroupArn=target_group_arn)
    response = conn.describe_target_groups()
    assert len(response["TargetGroups"]) == 0


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
    assert len(response.get("TargetGroups", [])) == 1


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
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Target group name 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' cannot be longer than '32' characters"
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
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == f"1 validation error detected: Value '{name}' at 'targetGroup.targetGroupArn.targetGroupName' failed to satisfy constraint: Member must satisfy regular expression pattern: (?!.*--)(?!^-)(?!.*-$)^[A-Za-z0-9-]+$"
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
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == f"Target group name '{name}' can only contain characters that are alphanumeric characters or hyphens(-)"
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
        HealthCheckTimeoutSeconds=3,
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
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    assert len(response["TargetGroups"]) == 1
    target_group_arn = target_group["TargetGroupArn"]

    # check if Names filter works
    response = conn.describe_target_groups(Names=[])
    assert len(response["TargetGroups"]) == 1
    response = conn.describe_target_groups(Names=["a-target"])
    assert len(response["TargetGroups"]) == 1
    target_group_arn = target_group["TargetGroupArn"]

    # The attributes should start with the defaults
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    assert len(response["Attributes"]) == 7
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    assert attributes["deregistration_delay.timeout_seconds"] == "300"
    assert attributes["stickiness.enabled"] == "false"
    assert attributes["waf.fail_open.enabled"] == "false"
    assert (
        attributes["load_balancing.cross_zone.enabled"]
        == "use_load_balancer_configuration"
    )

    # Add cookie stickiness
    response = conn.modify_target_group_attributes(
        TargetGroupArn=target_group_arn,
        Attributes=[
            {"Key": "stickiness.enabled", "Value": "true"},
            {"Key": "stickiness.type", "Value": "app_cookie"},
        ],
    )

    # The response should have only the keys updated
    assert len(response["Attributes"]) == 2
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    assert attributes["stickiness.type"] == "app_cookie"
    assert attributes["stickiness.enabled"] == "true"

    # These new values should be in the full attribute list
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    assert len(response["Attributes"]) == 7
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    assert attributes["stickiness.type"] == "app_cookie"
    assert attributes["stickiness.enabled"] == "true"


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
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        "Value /HTTP at 'healthCheckProtocol' failed to satisfy constraint"
        in err["Message"]
    )


@mock_elbv2
def test_describe_invalid_target_group():
    conn = boto3.client("elbv2", region_name="us-east-1")

    # Check error raises correctly
    with pytest.raises(ClientError) as exc:
        conn.describe_target_groups(Names=["invalid"])
    err = exc.value.response["Error"]
    assert err["Code"] == "TargetGroupNotFound"
    assert err["Message"] == "One or more target groups not found"


@mock_elbv2
@mock_ec2
def test_describe_target_groups():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    lb_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    groups = conn.describe_target_groups()["TargetGroups"]
    assert len(groups) == 0

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "201"},
    )
    arn_a = response["TargetGroups"][0]["TargetGroupArn"]

    conn.create_listener(
        LoadBalancerArn=lb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": arn_a}],
    )

    groups = conn.describe_target_groups()["TargetGroups"]
    assert len(groups) == 1
    assert groups[0]["Matcher"] == {"HttpCode": "201"}

    response = elbv2.create_target_group(
        Name="c-target",
        Protocol="HTTP",
        Port=8081,
        VpcId=vpc.id,
    )
    arn_c = response["TargetGroups"][0]["TargetGroupArn"]
    groups = conn.describe_target_groups()["TargetGroups"]
    assert len(groups) == 2
    assert groups[0]["TargetGroupName"] == "a-target"
    assert groups[1]["TargetGroupName"] == "c-target"

    response = elbv2.create_target_group(
        Name="b-target",
        Protocol="HTTP",
        Port=8082,
        VpcId=vpc.id,
    )
    arn_b = response["TargetGroups"][0]["TargetGroupArn"]
    groups = conn.describe_target_groups()["TargetGroups"]
    assert len(groups) == 3
    assert groups[0]["TargetGroupName"] == "a-target"
    assert groups[1]["TargetGroupName"] == "b-target"
    assert groups[2]["TargetGroupName"] == "c-target"

    groups = conn.describe_target_groups(Names=["a-target"])["TargetGroups"]
    assert len(groups) == 1
    assert groups[0]["TargetGroupName"] == "a-target"

    groups = conn.describe_target_groups(Names=["a-target", "b-target"])["TargetGroups"]
    assert len(groups) == 2
    assert groups[0]["TargetGroupName"] == "a-target"
    assert groups[1]["TargetGroupName"] == "b-target"

    groups = conn.describe_target_groups(TargetGroupArns=[arn_b])["TargetGroups"]
    assert len(groups) == 1
    assert groups[0]["TargetGroupName"] == "b-target"

    groups = conn.describe_target_groups(TargetGroupArns=[arn_b, arn_c])["TargetGroups"]
    assert len(groups) == 2
    assert groups[0]["TargetGroupName"] == "b-target"
    assert groups[1]["TargetGroupName"] == "c-target"

    groups = conn.describe_target_groups(LoadBalancerArn=lb_arn)["TargetGroups"]
    assert len(groups) == 1
    assert groups[0]["TargetGroupName"] == "a-target"

    response = conn.create_target_group(
        Name="d-target",
        Protocol="HTTP",
        Port=8082,
        VpcId=vpc.id,
    )
    arn_d = response["TargetGroups"][0]["TargetGroupArn"]
    conn.create_listener(
        LoadBalancerArn=lb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": arn_d}],
    )
    groups = conn.describe_target_groups(LoadBalancerArn=lb_arn)["TargetGroups"]
    assert len(groups) == 2
    assert groups[0]["TargetGroupName"] == "a-target"
    assert groups[1]["TargetGroupName"] == "d-target"


@mock_elbv2
@mock_ec2
def test_describe_target_groups_with_empty_load_balancer():
    response, _, _, _, _, conn = create_load_balancer()

    lb_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    with pytest.raises(ClientError) as exc:
        conn.describe_target_groups(LoadBalancerArn=lb_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "TargetGroupNotFound"
    assert err["Message"] == "One or more target groups not found"


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
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    arn = response["TargetGroups"][0]["TargetGroupArn"]

    client.modify_target_group(
        TargetGroupArn=arn,
        HealthCheckProtocol="HTTPS",
        HealthCheckPort="8081",
        HealthCheckPath="/status",
        HealthCheckIntervalSeconds=10,
        HealthCheckTimeoutSeconds=8,
        HealthyThresholdCount=10,
        UnhealthyThresholdCount=4,
        Matcher={"HttpCode": "200-399"},
    )

    response = client.describe_target_groups(TargetGroupArns=[arn])
    assert response["TargetGroups"][0]["Matcher"]["HttpCode"] == "200-399"
    assert response["TargetGroups"][0]["HealthCheckIntervalSeconds"] == 10
    assert response["TargetGroups"][0]["HealthCheckPath"] == "/status"
    assert response["TargetGroups"][0]["HealthCheckPort"] == "8081"
    assert response["TargetGroups"][0]["HealthCheckProtocol"] == "HTTPS"
    assert response["TargetGroups"][0]["HealthCheckTimeoutSeconds"] == 8
    assert response["TargetGroups"][0]["HealthyThresholdCount"] == 10
    assert response["TargetGroups"][0]["Protocol"] == "HTTP"
    assert response["TargetGroups"][0]["ProtocolVersion"] == "HTTP1"
    assert response["TargetGroups"][0]["UnhealthyThresholdCount"] == 4


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("target_type", ["instance", "ip", "lambda", "alb", "other"])
def test_create_target_group_with_target_type(target_type):
    response, vpc, _, _, _, conn = create_load_balancer()

    args = {
        "Name": "a-target",
        "TargetType": target_type,
    }

    if target_type != "lambda":
        args["Protocol"] = "HTTP"
        args["Port"] = 80
        args["VpcId"] = vpc.id

    response = conn.create_target_group(**args)

    group = response["TargetGroups"][0]
    assert "TargetGroupArn" in group
    assert group["TargetGroupName"] == "a-target"
    assert group["TargetType"] == target_type
    if target_type != "lambda":
        assert "Protocol" in group
        assert "VpcId" in group

    group = conn.describe_target_groups()["TargetGroups"][0]
    assert "TargetGroupArn" in group
    assert group["TargetGroupName"] == "a-target"
    assert group["TargetType"] == target_type
    if target_type != "lambda":
        assert "Protocol" in group
        assert "VpcId" in group


@mock_elbv2
@mock_ec2
def test_delete_target_group_after_modifying_listener():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id
    )
    target_group_arn1 = response["TargetGroups"][0]["TargetGroupArn"]

    response = client.create_target_group(
        Name="a-target-2", Protocol="HTTPS", Port=8081, VpcId=vpc.id
    )
    target_group_arn2 = response["TargetGroups"][0]["TargetGroupArn"]

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn1}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    client.modify_listener(
        ListenerArn=listener_arn,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn2}],
    )

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    default_actions = response["Listeners"][0]["DefaultActions"]
    assert default_actions == [{"Type": "forward", "TargetGroupArn": target_group_arn2}]

    # Target Group 1 can now be deleted, as the LB points to group 2
    client.delete_target_group(TargetGroupArn=target_group_arn1)

    # Sanity check - we're still pointing to group 2
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    default_actions = response["Listeners"][0]["DefaultActions"]
    assert default_actions == [{"Type": "forward", "TargetGroupArn": target_group_arn2}]


@mock_elbv2
@mock_ec2
def test_create_listener_with_multiple_target_groups():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id
    )
    target_group_arn1 = response["TargetGroups"][0]["TargetGroupArn"]

    response = client.create_target_group(
        Name="a-target-2", Protocol="HTTPS", Port=8081, VpcId=vpc.id
    )
    target_group_arn2 = response["TargetGroups"][0]["TargetGroupArn"]

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
    assert len(groups) == 2
    assert {"TargetGroupArn": target_group_arn1, "Weight": 100} in groups
    assert {"TargetGroupArn": target_group_arn2, "Weight": 0} in groups


@mock_elbv2
@mock_ec2
def test_create_listener_with_invalid_target_group():
    response, _, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

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
    assert err["Code"] == "TargetGroupNotFound"
    assert err["Message"] == "Target group 'unknown' not found"


@mock_elbv2
@mock_ec2
def test_delete_target_group_while_listener_still_exists():
    client = boto3.client("elbv2", region_name="us-east-1")

    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target", Protocol="HTTP", Port=8080, VpcId=vpc.id
    )
    target_group_arn1 = response["TargetGroups"][0]["TargetGroupArn"]

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
    assert err["Code"] == "ResourceInUse"
    assert (
        err["Message"]
        == f"The target group '{target_group_arn1}' is currently in use by a listener or a rule"
    )

    client.delete_listener(ListenerArn=listener_arn)

    # Deletion does succeed now that the listener is deleted
    client.delete_target_group(TargetGroupArn=target_group_arn1)


@mock_ec2
@mock_elbv2
def test_create_target_group_validation_error():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    _, vpc, _, _, _, _ = create_load_balancer()

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "A port must be specified"

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "A port must be specified"

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "A VPC ID must be specified"

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
            VpcId="non-existing",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == "The VPC ID 'non-existing' is not found"

    # When only the Interval is supplied, it can be the same value as the default
    group = elbv2.create_target_group(
        Name="target1",
        Port=443,
        Protocol="TLS",
        VpcId=vpc.id,
        TargetType="ip",
        IpAddressType="ipv6",
        HealthCheckIntervalSeconds=10,
        HealthCheckPort="traffic-port",
        HealthCheckProtocol="TCP",
        HealthyThresholdCount=3,
        UnhealthyThresholdCount=3,
    )["TargetGroups"][0]
    assert group["HealthCheckIntervalSeconds"] == 10
    assert group["HealthCheckTimeoutSeconds"] == 10

    # Same idea goes the other way around
    group = elbv2.create_target_group(
        Name="target2",
        Port=443,
        Protocol="TLS",
        VpcId=vpc.id,
        TargetType="ip",
        IpAddressType="ipv6",
        HealthCheckTimeoutSeconds=30,
        HealthCheckPort="traffic-port",
        HealthCheckProtocol="TCP",
        HealthyThresholdCount=3,
        UnhealthyThresholdCount=3,
    )["TargetGroups"][0]
    assert group["HealthCheckIntervalSeconds"] == 30
    assert group["HealthCheckTimeoutSeconds"] == 30

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(Name="a-target", TargetType="lambda", Port=8080)
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Port cannot be specified for target groups with target type 'lambda'"
    )

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target", TargetType="lambda", VpcId="non-existing"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "VPC ID cannot be specified for target groups with target type 'lambda'"
    )

    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            TargetType="lambda",
            Protocol="HTTP",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Protocol cannot be specified for target groups with target type 'lambda'"
    )


@mock_ec2
@mock_elbv2
@pytest.mark.parametrize(
    "protocol_name, should_raise",
    [
        ("HTTP", True),
        ("HTTPS", True),
        ("TCP", False),
        ("TLS", False),
        ("UDP", False),
        ("TCP_UDP", False),
    ],
)
def test_create_target_group_healthcheck_validation(protocol_name, should_raise):
    elbv2 = boto3.client("elbv2", region_name="us-east-1")

    _, vpc, _, _, _, _ = create_load_balancer()

    def _create_target_group(protocol_name, vpc, health_check_timeout_seconds):
        return elbv2.create_target_group(
            Name="a-target",
            Protocol=protocol_name,
            Port=80,
            VpcId=vpc,
            HealthCheckProtocol="HTTP",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=health_check_timeout_seconds,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
        )

    def _get_error_message(protocol_name, timeout, interval):
        if protocol_name in ["HTTP", "HTTPS"]:
            return f"Health check timeout '{timeout}' must be smaller than the interval '{interval}'"
        else:
            return f"Health check timeout '{timeout}' must be smaller than or equal to the interval '{interval}'"

    with pytest.raises(ClientError) as exc:
        _create_target_group(protocol_name, vpc.id, 6)
    assert exc.value.response["Error"]["Code"] == "ValidationError"
    assert exc.value.response["Error"]["Message"] == _get_error_message(
        protocol_name, 6, 5
    )

    if should_raise:
        with pytest.raises(ClientError) as exc:
            _create_target_group(protocol_name, vpc.id, 5)
        assert exc.value.response["Error"]["Code"] == "ValidationError"
        assert exc.value.response["Error"]["Message"] == _get_error_message(
            protocol_name, 5, 5
        )
