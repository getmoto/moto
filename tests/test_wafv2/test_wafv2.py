import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_helper_functions import CREATE_WEB_ACL_BODY, LIST_WEB_ACL_BODY


@mock_aws
@pytest.mark.parametrize(
    "region,partition",
    [("us-east-1", "aws"), ("cn-north-1", "aws-cn"), ("us-gov-east-1", "aws-us-gov")],
)
def test_create_web_acl(region, partition):
    conn = boto3.client("wafv2", region_name=region)
    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    web_acl = res["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith(
        f"arn:{partition}:wafv2:{region}:{ACCOUNT_ID}:regional/webacl/John/"
    )
    # Duplicate name - should raise error
    with pytest.raises(ClientError) as ex:
        conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    err = ex.value.response["Error"]
    assert (
        "AWS WAF could not perform the operation because some resource "
        "in your request is a duplicate of an existing one."
    ) in err["Message"]
    assert err["Code"] == "WafV2DuplicateItem"

    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Carl", "CLOUDFRONT"))
    web_acl = res["Summary"]
    assert web_acl.get("ARN").startswith(
        f"arn:aws:wafv2:global:{ACCOUNT_ID}:global/webacl/Carl/"
    )


@mock_aws
def test_create_web_acl_with_all_arguments():
    client = boto3.client("wafv2", region_name="us-east-2")
    web_acl_id = client.create_web_acl(
        Name="test",
        Scope="CLOUDFRONT",
        DefaultAction={"Allow": {}},
        Description="test desc",
        VisibilityConfig={
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "idk",
        },
        Rules=[
            {
                "Action": {"Allow": {}},
                "Name": "tf-acc-test-8205974093017792151-2",
                "Priority": 10,
                "Statement": {"GeoMatchStatement": {"CountryCodes": ["US", "NL"]}},
                "VisibilityConfig": {
                    "CloudWatchMetricsEnabled": False,
                    "MetricName": "tf-acc-test-8205974093017792151-2",
                    "SampledRequestsEnabled": False,
                },
            },
            {
                "Action": {"Count": {}},
                "Name": "tf-acc-test-8205974093017792151-1",
                "Priority": 5,
                "Statement": {
                    "SizeConstraintStatement": {
                        "ComparisonOperator": "LT",
                        "FieldToMatch": {"QueryString": {}},
                        "Size": 50,
                        "TextTransformations": [
                            {"Priority": 2, "Type": "CMD_LINE"},
                            {"Priority": 5, "Type": "NONE"},
                        ],
                    }
                },
                "VisibilityConfig": {
                    "CloudWatchMetricsEnabled": False,
                    "MetricName": "tf-acc-test-8205974093017792151-1",
                    "SampledRequestsEnabled": False,
                },
            },
        ],
    )["Summary"]["Id"]

    wacl = client.get_web_acl(Name="test", Scope="CLOUDFRONT", Id=web_acl_id)["WebACL"]
    assert wacl["Description"] == "test desc"
    assert wacl["DefaultAction"] == {"Allow": {}}
    assert wacl["VisibilityConfig"] == {
        "SampledRequestsEnabled": False,
        "CloudWatchMetricsEnabled": False,
        "MetricName": "idk",
    }
    assert len(wacl["Rules"]) == 2


@mock_aws
def test_get_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    body = CREATE_WEB_ACL_BODY("John", "REGIONAL")
    web_acl_id = conn.create_web_acl(**body)["Summary"]["Id"]
    wacl = conn.get_web_acl(Name="John", Scope="REGIONAL", Id=web_acl_id)["WebACL"]
    assert wacl["Name"] == "John"
    assert wacl["Id"] == web_acl_id


@mock_aws
def test_list_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Penelope", "CLOUDFRONT"))
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Sarah", "REGIONAL"))
    res = conn.list_web_acls(**LIST_WEB_ACL_BODY("REGIONAL"))
    web_acls = res["WebACLs"]
    assert len(web_acls) == 2
    assert web_acls[0]["Name"] == "Daphne"
    assert web_acls[1]["Name"] == "Sarah"

    res = conn.list_web_acls(**LIST_WEB_ACL_BODY("CLOUDFRONT"))
    web_acls = res["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Penelope"


@mock_aws
def test_delete_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl_id = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))[
        "Summary"
    ]["Id"]

    conn.delete_web_acl(Name="Daphne", Id=wacl_id, Scope="REGIONAL", LockToken="n/a")

    res = conn.list_web_acls(**LIST_WEB_ACL_BODY("REGIONAL"))
    assert len(res["WebACLs"]) == 0

    with pytest.raises(ClientError) as exc:
        conn.get_web_acl(Name="Daphne", Scope="REGIONAL", Id=wacl_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "WAFNonexistentItemException"
    assert err["Message"] == (
        "AWS WAF couldn’t perform the operation because your resource doesn’t exist."
    )


@mock_aws
def test_update_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl_id = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))[
        "Summary"
    ]["Id"]

    resp = conn.update_web_acl(
        Name="Daphne",
        Scope="REGIONAL",
        Id=wacl_id,
        DefaultAction={"Block": {"CustomResponse": {"ResponseCode": 412}}},
        Description="updated_desc",
        Rules=[
            {
                "Name": "rule1",
                "Priority": 456,
                "Statement": {},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": "updated",
                },
            }
        ],
        LockToken="n/a",
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "updated",
        },
    )
    assert "NextLockToken" in resp

    acl = conn.get_web_acl(Name="Daphne", Scope="REGIONAL", Id=wacl_id)["WebACL"]
    assert acl["Description"] == "updated_desc"
    assert acl["DefaultAction"] == {"Block": {"CustomResponse": {"ResponseCode": 412}}}
    assert acl["Rules"] == [
        {
            "Name": "rule1",
            "Priority": 456,
            "Statement": {},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": "updated",
            },
        }
    ]
    assert acl["VisibilityConfig"] == {
        "SampledRequestsEnabled": True,
        "CloudWatchMetricsEnabled": True,
        "MetricName": "updated",
    }


@mock_aws
def test_ip_set_crud():
    client = boto3.client("wafv2", region_name="us-east-1")

    create_response = client.create_ip_set(
        Name="test-ip-set",
        Scope="CLOUDFRONT",
        Description="Test IP set",
        IPAddressVersion="IPV4",
        Addresses=["192.168.0.1/32", "10.0.0.0/8"],
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    assert "Summary" in create_response
    summary = create_response["Summary"]

    assert summary["Id"]
    assert summary["LockToken"]
    assert summary["ARN"]
    assert summary["Name"] == "test-ip-set"
    assert "Test IP set" in summary["Description"]

    get_response = client.get_ip_set(
        Name=summary["Name"], Scope="CLOUDFRONT", Id=summary["Id"]
    )
    assert "IPSet" in get_response
    assert "LockToken" in get_response

    ip_set = get_response["IPSet"]
    assert ip_set["IPAddressVersion"] == "IPV4"

    with pytest.raises(ClientError) as e:
        client.update_ip_set(
            Name="test-ip-set",
            Scope="CLOUDFRONT",
            Id=summary["Id"],
            Addresses=["10.0.0.0/8"],
            LockToken="aaaaaaaaaaaaaaaaaa",  # invalid lock token
        )
    e.value.response["Error"]["Code"] == "WAFOptimisticLockException"
    e.value.response["Error"][
        "Message"
    ] == "AWS WAF couldn’t save your changes because someone changed the resource after you started to edit it. Reapply your changes."

    update_response = client.update_ip_set(
        Name="test-ip-set",
        Scope="CLOUDFRONT",
        Id=summary["Id"],
        Description="Updated test IP set",
        Addresses=["192.168.1.0/24", "10.0.0.0/8"],
        LockToken=get_response["LockToken"],
    )

    assert "NextLockToken" in update_response

    updated_get_response = client.get_ip_set(
        Name=summary["Name"], Scope="CLOUDFRONT", Id=summary["Id"]
    )

    updated_ip_set = updated_get_response["IPSet"]
    assert updated_ip_set["Description"] == "Updated test IP set"
    assert updated_get_response["LockToken"] == update_response["NextLockToken"]
    assert all(
        addr in ["192.168.1.0/24", "10.0.0.0/8"] for addr in updated_ip_set["Addresses"]
    )

    list_response = client.list_ip_sets(Scope="CLOUDFRONT")
    assert len(list_response["IPSets"]) == 1

    assert all(
        [
            key in list_response["IPSets"][0]
            for key in ["ARN", "Description", "Id", "LockToken", "Name"]
        ]
    )
    assert "NextMarker" in list_response

    client.delete_ip_set(
        Name=summary["Name"],
        Scope="CLOUDFRONT",
        Id=summary["Id"],
        LockToken=updated_get_response["LockToken"],
    )

    with pytest.raises(ClientError) as e:
        client.get_ip_set(Name=summary["Name"], Scope="CLOUDFRONT", Id=summary["Id"])
    e.value.response["Error"]["Code"] == "WAFNonexistentItemException"
    e.value.response["Error"][
        "Message"
    ] == "AWS WAF couldn’t perform the operation because your resource doesn’t exist."


@mock_aws
def test_logging_configuration_crud():
    wafv2_client = boto3.client("wafv2", region_name="us-east-1")
    create_web_acl_response = wafv2_client.create_web_acl(
        Name="TestWebACL",
        Scope="REGIONAL",
        DefaultAction={"Allow": {}},
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "TestWebACLMetric",
        },
        Rules=[],
    )
    web_acl_arn = create_web_acl_response["Summary"]["ARN"]

    # Create log groups
    logs_client = boto3.client("logs", region_name="us-east-1")
    logs_client.create_log_group(logGroupName="aws-waf-logs-test")
    log_group = logs_client.describe_log_groups(logGroupNamePrefix="aws-waf-logs-test")[
        "logGroups"
    ][0]

    create_response = wafv2_client.put_logging_configuration(
        LoggingConfiguration={
            "ResourceArn": web_acl_arn,
            "LogDestinationConfigs": [log_group["arn"]],
        }
    )

    assert "LoggingConfiguration" in create_response
    logging_configuration = create_response["LoggingConfiguration"]
    assert logging_configuration["ResourceArn"]

    get_response = wafv2_client.get_logging_configuration(
        ResourceArn=logging_configuration["ResourceArn"]
    )
    assert "LoggingConfiguration" in get_response

    list_response = wafv2_client.list_logging_configurations(
        Scope="REGIONAL",
    )
    assert len(list_response["LoggingConfigurations"]) > 0

    wafv2_client.delete_logging_configuration(
        ResourceArn=logging_configuration["ResourceArn"],
    )

    with pytest.raises(ClientError) as e:
        wafv2_client.get_logging_configuration(
            ResourceArn=logging_configuration["ResourceArn"]
        )
    e.value.response["Error"]["Code"] == "WAFNonexistentItemException"
