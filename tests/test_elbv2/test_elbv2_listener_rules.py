import boto3
from botocore.exceptions import ClientError
import pytest
import sure  # noqa # pylint: disable=unused-import

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
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal([condition])

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)  # including the default rule

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal([condition])
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


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
    response["Rules"].should.have.length_of(1)
    modified_rule = response.get("Rules")[0]
    modified_rule["Conditions"].should.equal([modify_condition])


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
            {"Field": "source-ip",},
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
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(expected_message)
