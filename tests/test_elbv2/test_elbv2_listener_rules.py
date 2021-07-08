from __future__ import unicode_literals

import boto3
import botocore
from botocore.exceptions import ClientError
import pytest
import sure  # noqa

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
def test_create_rule_with_one_path_pattern_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[{"Field": "path-pattern", "Values": ["/home"]}],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal([{"Field": "path-pattern", "Values": ["/home"]}])

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal([{"Field": "path-pattern", "Values": ["/home"]}])
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_create_rule_with_many_path_pattern_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            },
        ],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            }
        ]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            }
        ]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_modify_rule_path_pattern_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[{"Field": "path-pattern", "Values": ["/home"]}],
        Actions=[default_action],
    )
    rule = response.get("Rules")[0]

    # modify_rule
    response = conn.modify_rule(
        RuleArn=rule["RuleArn"],
        Conditions=[
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            }
        ],
    )
    response["Rules"].should.have.length_of(1)
    modified_rule = response.get("Rules")[0]
    modified_rule["Conditions"].should.equal(
        [
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/home", "/about"]},
            }
        ]
    )


@mock_elbv2
@mock_ec2
def test_create_rule_with_one_host_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[{"Field": "host-header", "Values": ["example.com"]}],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [{"Field": "host-header", "Values": ["example.com"]}]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [{"Field": "host-header", "Values": ["example.com"]}]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_create_rule_with_many_host_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            },
        ],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            }
        ]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            }
        ]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_modify_rule_host_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[{"Field": "host-header", "Values": ["example.com"]}],
        Actions=[default_action],
    )
    rule = response.get("Rules")[0]

    # modify_rule
    response = conn.modify_rule(
        RuleArn=rule["RuleArn"],
        Conditions=[
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            }
        ],
    )
    response["Rules"].should.have.length_of(1)
    modified_rule = response.get("Rules")[0]
    modified_rule["Conditions"].should.equal(
        [
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["example.com", "www.example.com"]},
            }
        ]
    )


@mock_elbv2
@mock_ec2
def test_create_rule_with_http_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla"],
                },
            },
        ],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla"],
                },
            }
        ]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla"],
                },
            }
        ]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_create_rule_with_http_request_method_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[
            {
                "Field": "http-request-method",
                "HttpRequestMethodConfig": {"Values": ["GET", "POST"]},
            }
        ],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [
            {
                "Field": "http-request-method",
                "HttpRequestMethodConfig": {"Values": ["GET", "POST"]},
            }
        ]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [
            {
                "Field": "http-request-method",
                "HttpRequestMethodConfig": {"Values": ["GET", "POST"]},
            }
        ]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_create_rule_with_query_string_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule
    response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=100,
        Conditions=[
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "hello", "Value": "world"}]},
            },
        ],
        Actions=[default_action],
    )

    # assert create_rule response
    response["Rules"].should.have.length_of(1)
    rule = response.get("Rules")[0]
    rule["Priority"].should.equal("100")
    rule["Conditions"].should.equal(
        [
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "hello", "Value": "world"}]},
            }
        ]
    )

    # assert describe_rules response
    response = conn.describe_rules(ListenerArn=http_listener_arn)
    response["Rules"].should.have.length_of(2)

    # assert describe_rules with arn filter response
    rule = response["Rules"][0]
    rule["Conditions"].should.equal(
        [
            {
                "Field": "query-string",
                "QueryStringConfig": {"Values": [{"Key": "hello", "Value": "world"}]},
            }
        ]
    )
    response = conn.describe_rules(RuleArns=[rule["RuleArn"]])
    response["Rules"].should.equal([rule])


@mock_elbv2
@mock_ec2
def test_create_rule_validate_host_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule with long host header
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "host-header", "Values": ["x" * 256]}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'host-header' value is too long; the limit is '128'"
    )

    # create_rule with long host header
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {"Field": "host-header", "HostHeaderConfig": {"Values": ["x" * 256]}}
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'host-header' value is too long; the limit is '128'"
    )

    # create_rule with too many values
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "host-header", "Values": ["one", "two"]}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'host-header' field contains too many values; the limit is '1'"
    )

    # create_rule with no value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "host-header"}],
            Actions=[default_action],
        )

    # create_rule with empty value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": []}}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("A condition value must be specified")


@mock_elbv2
@mock_ec2
def test_create_rule_validate_path_pattern_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule with long path pattern
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "path-pattern", "Values": ["x" * 256]}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'path-pattern' value is too long; the limit is '128'"
    )

    # create_rule with long path pattern
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {"Field": "path-pattern", "PathPatternConfig": {"Values": ["x" * 256]}}
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'path-pattern' value is too long; the limit is '128'"
    )

    # create_rule with too many values
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "path-pattern", "Values": ["one", "two"]}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'path-pattern' field contains too many values; the limit is '1'"
    )

    # create_rule with no value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "path-pattern"}],
            Actions=[default_action],
        )

    # create_rule with empty value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "path-pattern", "PathPatternConfig": {"Values": []}}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("A condition value must be specified")


@mock_elbv2
@mock_ec2
def test_create_rule_validate_http_header_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule with long http header name
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "http-header",
                    "HttpHeaderConfig": {"HttpHeaderName": "x" * 50, "Values": ["y"]},
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'HttpHeaderName' value is too long; the limit is '40'"
    )

    # create_rule with long http header value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "http-header",
                    "HttpHeaderConfig": {"HttpHeaderName": "x", "Values": ["y" * 256]},
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'http-header' value is too long; the limit is '128'"
    )


@mock_elbv2
@mock_ec2
def test_create_rule_validate_http_request_method_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule with long host header
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "http-request-method",
                    "HttpRequestMethodConfig": {"Values": ["get"]},
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'http-request-method' value is invalid; the allowed characters are A-Z, hyphen and underscore"
    )

    # create_rule with long host header
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "http-request-method",
                    "HttpRequestMethodConfig": {"Values": ["X" * 50]},
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "The 'http-request-method' value is too long; the limit is '40'"
    )

    # create_rule with no config
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[{"Field": "http-request-method",}],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "A 'HttpRequestMethodConfig' must be specified with 'http-request-method'"
    )


@mock_elbv2
@mock_ec2
def test_create_rule_validate_query_string_condition():
    conn = boto3.client("elbv2", region_name="us-east-1")

    http_listener_arn = setup_listener(conn)

    # create_rule with long key
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "query-string",
                    "QueryStringConfig": {
                        "Values": [{"Key": "x" * 256, "Value": "world"}]
                    },
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("The 'Key' value is too long; the limit is '128'")

    # create_rule with long value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "query-string",
                    "QueryStringConfig": {
                        "Values": [{"Key": "hello", "Value": "x" * 256}]
                    },
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal("The 'Value' value is too long; the limit is '128'")

    # create_rule without value
    with pytest.raises(ClientError) as ex:
        response = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=100,
            Conditions=[
                {
                    "Field": "query-string",
                    "QueryStringConfig": {"Values": [{"Key": "hello"}]},
                }
            ],
            Actions=[default_action],
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.equal(
        "A 'Value' must be specified in 'QueryStringKeyValuePair'"
    )
