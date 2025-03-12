import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_helper_functions import CREATE_WEB_ACL_BODY


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
        f"arn:aws:wafv2:us-east-1:{ACCOUNT_ID}:global/webacl/Carl/"
    )


@mock_aws
def test_create_web_acl_with_all_arguments():
    client = boto3.client("wafv2", region_name="us-east-2")
    rule_1 = {
        "Action": {"Allow": {}},
        "Name": "tf-acc-test-8205974093017792151-2",
        "Priority": 10,
        "Statement": {"GeoMatchStatement": {"CountryCodes": ["US", "NL"]}},
        "VisibilityConfig": {
            "CloudWatchMetricsEnabled": False,
            "MetricName": "tf-acc-test-8205974093017792151-2",
            "SampledRequestsEnabled": False,
        },
    }
    rule_2 = {
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
    }
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
        AssociationConfig={
            "RequestBody": {
                "Test": {
                    "DefaultSizeInspectionLimit": "KB_64",
                },
            },
        },
        CustomResponseBodies={
            "Test": {
                "Content": "test",
                "ContentType": "TEXT_PLAIN",
            },
        },
        CaptchaConfig={
            "ImmunityTimeProperty": {"ImmunityTime": 60},
        },
        ChallengeConfig={
            "ImmunityTimeProperty": {"ImmunityTime": 60},
        },
        TokenDomains=[
            "test1.com",
            "test2.com",
        ],
        Tags=[
            {"Key": "TestKey", "Value": "TestValue"},
        ],
        Rules=[
            rule_1,
            rule_2,
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
    assert rule_1 in wacl["Rules"] and rule_2 in wacl["Rules"]
    assert wacl["AssociationConfig"] == {
        "RequestBody": {
            "Test": {
                "DefaultSizeInspectionLimit": "KB_64",
            },
        },
    }
    assert wacl["CustomResponseBodies"] == {
        "Test": {
            "Content": "test",
            "ContentType": "TEXT_PLAIN",
        },
    }
    assert wacl["CaptchaConfig"] == {
        "ImmunityTimeProperty": {"ImmunityTime": 60},
    }
    assert wacl["ChallengeConfig"] == {
        "ImmunityTimeProperty": {"ImmunityTime": 60},
    }
    assert wacl["TokenDomains"] == ["test1.com", "test2.com"]


@mock_aws
def test_get_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    body = CREATE_WEB_ACL_BODY("John", "REGIONAL")
    web_acl_id = conn.create_web_acl(**body)["Summary"]["Id"]
    wacl = conn.get_web_acl(Name="John", Scope="REGIONAL", Id=web_acl_id)["WebACL"]
    assert wacl["Name"] == "John"
    assert wacl["Id"] == web_acl_id
    assert wacl["LabelNamespace"] == f"awswaf:{ACCOUNT_ID}:webacl:John:"


@mock_aws
def test_list_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Penelope", "CLOUDFRONT"))
    for idx in range(5):
        conn.create_web_acl(**CREATE_WEB_ACL_BODY(f"Sarah {idx}", "REGIONAL"))
    res = conn.list_web_acls(Scope="REGIONAL")
    web_acls = res["WebACLs"]
    assert len(web_acls) == 6
    assert web_acls[0]["Name"] == "Daphne"
    assert web_acls[1]["Name"] == "Sarah 0"

    res = conn.list_web_acls(Scope="CLOUDFRONT")
    web_acls = res["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Penelope"

    page1 = conn.list_web_acls(Scope="REGIONAL", Limit=2)
    assert len(page1["WebACLs"]) == 2

    page2 = conn.list_web_acls(
        Scope="REGIONAL", Limit=1, NextMarker=page1["NextMarker"]
    )
    assert len(page2["WebACLs"]) == 1

    page3 = conn.list_web_acls(Scope="REGIONAL", NextMarker=page2["NextMarker"])
    assert len(page3["WebACLs"]) == 3


@mock_aws
def test_delete_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))["Summary"]

    with pytest.raises(ClientError) as e:
        conn.delete_web_acl(
            Name="Daphne", Id=wacl["Id"], Scope="REGIONAL", LockToken="123"
        )
    assert e.value.response["Error"]["Code"] == "WAFOptimisticLockException"

    conn.delete_web_acl(
        Name="Daphne", Id=wacl["Id"], Scope="REGIONAL", LockToken=wacl["LockToken"]
    )

    res = conn.list_web_acls(Scope="REGIONAL")
    assert len(res["WebACLs"]) == 0

    with pytest.raises(ClientError) as exc:
        conn.get_web_acl(Name="Daphne", Scope="REGIONAL", Id=wacl["Id"])
    err = exc.value.response["Error"]
    assert err["Code"] == "WAFNonexistentItemException"
    assert err["Message"] == (
        "AWS WAF couldn’t perform the operation because your resource doesn’t exist."
    )


@mock_aws
def test_update_web_acl():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))["Summary"]

    resp = conn.update_web_acl(
        Name="Daphne",
        Scope="REGIONAL",
        Id=wacl["Id"],
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
        LockToken=wacl["LockToken"],
        VisibilityConfig={
            "SampledRequestsEnabled": True,
            "CloudWatchMetricsEnabled": True,
            "MetricName": "updated",
        },
    )
    assert "NextLockToken" in resp

    with pytest.raises(ClientError) as e:
        conn.update_web_acl(
            Name="Daphne",
            Scope="REGIONAL",
            Id=wacl["Id"],
            DefaultAction={"Block": {"CustomResponse": {"ResponseCode": 412}}},
            LockToken="123",
            VisibilityConfig={
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": "updated",
            },
        )
    assert e.value.response["Error"]["Code"] == "WAFOptimisticLockException"

    acl = conn.get_web_acl(Name="Daphne", Scope="REGIONAL", Id=wacl["Id"])["WebACL"]
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
def test_list_ip_sets_pagination():
    client = boto3.client("wafv2", region_name="us-east-1")

    for idx in range(10):
        client.create_ip_set(
            Name=f"test-ip-set-{idx}",
            Scope="CLOUDFRONT",
            Description="Test IP set",
            IPAddressVersion="IPV4",
            Addresses=["192.168.0.1/32", "10.0.0.0/8"],
            Tags=[{"Key": "Environment", "Value": "Test"}],
        )

    list_all = client.list_ip_sets(Scope="CLOUDFRONT")["IPSets"]
    assert len(list_all) == 10

    page1 = client.list_ip_sets(Scope="CLOUDFRONT", Limit=2)
    assert len(page1["IPSets"]) == 2

    page2 = client.list_ip_sets(
        Scope="CLOUDFRONT", Limit=5, NextMarker=page1["NextMarker"]
    )
    assert len(page2["IPSets"]) == 5

    page3 = client.list_ip_sets(Scope="CLOUDFRONT", NextMarker=page2["NextMarker"])
    assert len(page3["IPSets"]) == 3
