import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_elbv2, mock_ec2

default_action = {
    "FixedResponseConfig": {"StatusCode": "200", "ContentType": "text/plain"},
    "Type": "fixed-response",
}


def setup_listener(conn):
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "StatusCode": "503",
                    "ContentType": "text/plain",
                },
            }
        ],
    )
    listener = response.get("Listeners")[0]
    http_listener_arn = listener.get("ListenerArn")
    return http_listener_arn


def setup_target_group(boto_client):

    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    response = boto_client.create_target_group(
        Name="target-group-name", Protocol="HTTP", Port=80, VpcId=vpc.id
    )

    target_group = response.get("TargetGroups")[0]
    target_group_arn = target_group.get("TargetGroupArn")

    return target_group_arn


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize(
    "condition",
    [
        {"Field": "host-header", "Values": ["example.com"]},
        {
            "Field": "host-header",
            "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
        },
        {
            "Field": "http-header",
            "HttpHeaderConfig": {
                "HttpHeaderName": "User-Agent",
                "Values": ["Mozilla"],
            },
        },
        {
            "Field": "http-request-method",
            "HttpRequestMethodConfig": {"Values": ["GET", "POST"]},
        },
        {"Field": "path-pattern", "Values": ["/home"]},
        {
            "Field": "path-pattern",
            "PathPatternConfig": {"Values": ["/home", "/about"]},
        },
        {
            "Field": "query-string",
            "QueryStringConfig": {"Values": [{"Key": "hello", "Value": "world"}]},
        },
        {"Field": "source-ip", "SourceIpConfig": {"Values": ["172.28.7.0/24"]}},
    ],
)
def test_create_rule_condition(condition):
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[condition],
        Actions=[default_action],
    )

    # assert create_rule response
    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "100"
    assert rule["Conditions"] == [condition]

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    assert len(response["Rules"]) == 2  # including the default rule

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    assert rule["Conditions"] == [condition]
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    assert response["Rules"] == [rule]

    # assert describe_tags response
    response = conn.describe_tags(ResourceArns=[rule["RuleArn"]])
    assert len(response["TagDescriptions"]) == 1


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize(
    "create_condition,modify_condition",
    [
        (
            {"Field": "host-header", "Values": ["example.com"]},
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            },
        ),
        (
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla"],
                },
            },
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla", "curl"],
                },
            },
        ),
        (
            {"Field": "path-pattern", "Values": ["/home"]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            },
        ),
    ],
)
def test_modify_rule_condition(create_condition, modify_condition):
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[create_condition],
        Actions=[default_action],
    )
    rule = response.get("Rules")[0]

    # modify_rule
    response = conn.modify_rule(RuleArn=rule["RuleArn"], Conditions=[modify_condition])
    assert len(response["Rules"]) == 1
    modified_rule = response.get("Rules")[0]
    assert modified_rule["Conditions"] == [modify_condition]


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize(
    "condition,expected_message",
    [
        (
            {"Field": "host-header", "Values": ["x" * 256]},
            "The 'host-header' value is too long; the limit is '128'",
        ),
        (
            {"Field": "host-header", "HostHeaderConfig": {"Values": ["x" * 256]}},
            "The 'host-header' value is too long; the limit is '128'",
        ),
        (
            {"Field": "host-header", "Values": ["one", "two"]},
            "The 'host-header' field contains too many values; the limit is '1'",
        ),
        ({"Field": "host-header"}, "A condition value must be specified"),
        (
            {"Field": "host-header", "HostHeaderConfig": {"Values": []}},
            "A condition value must be specified",
        ),
        (
            {"Field": "path-pattern", "Values": ["x" * 256]},
            "The 'path-pattern' value is too long; the limit is '128'",
        ),
        (
            {"Field": "path-pattern", "PathPatternConfig": {"Values": ["x" * 256]}},
            "The 'path-pattern' value is too long; the limit is '128'",
        ),
        (
            {"Field": "path-pattern", "Values": ["one", "two"]},
            "The 'path-pattern' field contains too many values; the limit is '1'",
        ),
        ({"Field": "path-pattern"}, "A condition value must be specified"),
        (
            {"Field": "path-pattern", "PathPatternConfig": {"Values": []}},
            "A condition value must be specified",
        ),
        (
            {
                "Field": "http-header",
                "HttpHeaderConfig": {"HttpHeaderName": "x" * 50, "Values": ["y"]},
            },
            "The 'HttpHeaderName' value is too long; the limit is '40'",
        ),
        (
            {
                "Field": "http-header",
                "HttpHeaderConfig": {"HttpHeaderName": "x", "Values": ["y" * 256]},
            },
            "The 'http-header' value is too long; the limit is '128'",
        ),
        (
            {
                "Field": "http-request-method",
                "HttpRequestMethodConfig": {"Values": ["get"]},
            },
            "The 'http-request-method' value is invalid; the allowed characters are A-Z, hyphen and underscore",
        ),
        (
            {
                "Field": "http-request-method",
                "HttpRequestMethodConfig": {"Values": ["X" * 50]},
            },
            "The 'http-request-method' value is too long; the limit is '40'",
        ),
        (
            {"Field": "http-request-method"},
            "A 'HttpRequestMethodConfig' must be specified with 'http-request-method'",
        ),
        (
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "x" * 256, "Value": "world"}]},
            },
            "The 'Key' value is too long; the limit is '128'",
        ),
        (
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "hello", "Value": "x" * 256}]},
            },
            "The 'Value' value is too long; the limit is '128'",
        ),
        (
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "hello"}]},
            },
            "A 'Value' must be specified in 'QueryStringKeyValuePair'",
        ),
        (
            {"Field": "source-ip", "SourceIpConfig": {"Values": []}},
            "A 'source-ip' value must be specified",
        ),
        (
            {"Field": "source-ip"},
            "A 'SourceIpConfig' must be specified with 'source-ip'",
        ),
    ],
)
def test_create_rule_validate_condition(condition, expected_message):
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    with pytest.raises(ClientError) as ex:
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[condition],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert err["Message"] == expected_message


@mock_elbv2
@mock_ec2
def test_describe_unknown_rule():
    conn = boto3.client("elbv2", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        conn.describe_rules(RuleArns=["unknown_arn"])
    err = exc.value.response["Error"]
    assert err["Code"] == "RuleNotFound"
    assert err["Message"] == "One or more rules not found"


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize(
    "action",
    [
        (
            {
                "Type": "authenticate-oidc",
                "AuthenticateOidcConfig": {
                    "Issuer": "https://example.com/path",
                    "AuthorizationEndpoint": "https://example.com/path",
                    "TokenEndpoint": "https://example.com/path",
                    "UserInfoEndpoint": "https://example.com/path",
                    "ClientId": "id",
                    "ClientSecret": "secret",
                    "SessionCookieName": "cookie",
                    "Scope": "openid",
                    "SessionTimeout": 60,
                    "AuthenticationRequestExtraParams": {"extra": "param"},
                    "OnUnauthenticatedRequest": "deny",
                    "UseExistingClientSecret": False,
                },
            }
        ),
        (
            {
                "Type": "authenticate-cognito",
                "AuthenticateCognitoConfig": {
                    "UserPoolArn": "arn:user-pool",
                    "UserPoolClientId": "id",
                    "UserPoolDomain": "domain",
                    "SessionCookieName": "cookie",
                    "Scope": "openid",
                    "SessionTimeout": 60,
                    "AuthenticationRequestExtraParams": {"extra": "param"},
                    "OnUnauthenticatedRequest": "deny",
                },
            }
        ),
        (
            {
                "Type": "redirect",
                "RedirectConfig": {
                    "Protocol": "HTTPS",
                    "Port": "1",
                    "Host": "host",
                    "Path": "/path",
                    "Query": "query",
                    "StatusCode": "HHTP 301",
                },
            }
        ),
        (
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "MessageBody": "message body",
                    "ContentType": "text/plain",
                    "StatusCode": "503",
                },
            }
        ),
    ],
)
def test_create_rule_action(action):
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[],
        Actions=[action],
    )

    # assert create_rule response
    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "100"
    assert rule["Conditions"] == []
    assert rule["Actions"] == [action]

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    assert len(response["Rules"]) == 2  # including the default rule
    rule = response.get("Rules")[0]
    assert rule["Actions"][0] == action

    # assert set_rule_priorities response
    rule_arn = response.get("Rules")[0]["RuleArn"]
    response = conn.set_rule_priorities(
        RulePriorities=[{"RuleArn": rule_arn, "Priority": 99}]
    )

    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "99"
    assert rule["Conditions"] == []
    assert rule["Actions"][0] == action


@mock_elbv2
@mock_ec2
def test_create_rule_action_forward_config():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)
    target_group_arn = setup_target_group(conn)

    forward_config = {
        "TargetGroups": [{"TargetGroupArn": target_group_arn, "Weight": 100}],
        "TargetGroupStickinessConfig": {"Enabled": False},
    }
    action = {"Order": 1, "Type": "forward", "ForwardConfig": forward_config}

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[],
        Actions=[action],
    )

    # assert create_rule response
    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "100"
    assert rule["Conditions"] == []
    assert rule["Actions"][0] == action

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    assert len(response["Rules"]) == 2  # including the default rule
    rule = response.get("Rules")[0]
    assert rule["Actions"][0] == action

    # assert set_rule_priorities response
    rule_arn = response.get("Rules")[0]["RuleArn"]
    response = conn.set_rule_priorities(
        RulePriorities=[{"RuleArn": rule_arn, "Priority": 99}]
    )

    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "99"
    assert rule["Conditions"] == []
    assert rule["Actions"][0] == action


@mock_elbv2
@mock_ec2
def test_create_rule_action_forward_target_group():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)
    target_group_arn = setup_target_group(conn)

    action = {"Order": 1, "Type": "forward", "TargetGroupArn": target_group_arn}

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[],
        Actions=[action],
    )

    # assert create_rule response
    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "100"
    assert rule["Conditions"] == []
    assert rule["Actions"][0] == action

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    assert len(response["Rules"]) == 2  # including the default rule
    rule = response.get("Rules")[0]
    assert rule["Actions"][0] == action

    # assert set_rule_priorities
    rule_arn = response.get("Rules")[0]["RuleArn"]
    response = conn.set_rule_priorities(
        RulePriorities=[{"RuleArn": rule_arn, "Priority": 99}]
    )

    # assert set_rule_priorities response
    assert len(response["Rules"]) == 1
    rule = response.get("Rules")[0]
    assert rule["Priority"] == "99"
    assert rule["Conditions"] == []
    assert rule["Actions"][0] == action

    # assert describe_target_group by loadbalancer_arn response
    load_balancer_arn = conn.describe_listeners(ListenerArns=[http_listener_arn])[
        "Listeners"
    ][0]["LoadBalancerArn"]
    response = conn.describe_target_groups(LoadBalancerArn=load_balancer_arn)
    assert len(response.get("TargetGroups")) == 1
