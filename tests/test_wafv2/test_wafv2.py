import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_wafv2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from .test_helper_functions import CREATE_WEB_ACL_BODY, LIST_WEB_ACL_BODY


@mock_wafv2
def test_create_web_acl():

    conn = boto3.client("wafv2", region_name="us-east-1")
    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    web_acl = res["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith(
        f"arn:aws:wafv2:us-east-1:{ACCOUNT_ID}:regional/webacl/John/"
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


@mock_wafv2
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


@mock_wafv2
def test_get_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    body = CREATE_WEB_ACL_BODY("John", "REGIONAL")
    web_acl_id = conn.create_web_acl(**body)["Summary"]["Id"]
    wacl = conn.get_web_acl(Name="John", Scope="REGIONAL", Id=web_acl_id)["WebACL"]
    assert wacl["Name"] == "John"
    assert wacl["Id"] == web_acl_id


@mock_wafv2
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


@mock_wafv2
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


@mock_wafv2
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
