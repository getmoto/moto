from __future__ import unicode_literals
import json
import pytest

import sure  # noqa

import boto3
import botocore
from botocore.exceptions import ClientError
import moto.server as server
from moto import mock_wafv2, mock_elbv2, mock_ec2
from .test_helper_functions import (
    CREATE_ASSOCIATE_WEB_ACL_BODY,
    CREATE_WEB_ACL_BODY,
    LIST_WEB_ACL_BODY,
    CREATE_DISASSOCIATE_WEB_ACL_BODY,
    CREATE_GET_WEB_ACL_FOR_RESOURCE_BODY,
    create_alb,
)
from moto.core import ACCOUNT_ID

CREATE_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.CreateWebACL",
    "Content-Type": "application/json",
}


LIST_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.ListWebACLs",
    "Content-Type": "application/json",
}

ASSOCIATE_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.AssociateWebACL",
    "Content-Type": "application/json",
}


DISASSOCIATE_WEB_ACL_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.DisassociateWebACL",
    "Content-Type": "application/json",
}

GET_WEB_ACL_FOR_RESOURCE_HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.GetWebACLForResource",
    "Content-Type": "application/json",
}


@mock_wafv2
def test_create_web_acl():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    assert res.status_code == 200

    web_acl = res.json["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith(
        "arn:aws:wafv2:us-east-1:{}:regional/webacl/John/".format(ACCOUNT_ID)
    )

    # Duplicate name - should raise error
    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because some resource in your request is a duplicate of an existing one."
        in res.data
    )
    assert b"WafV2DuplicateItem" in res.data

    res = test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("Carl", "CLOUDFRONT"),
    )
    web_acl = res.json["Summary"]
    assert web_acl.get("ARN").startswith(
        "arn:aws:wafv2:global:{}:global/webacl/Carl/".format(ACCOUNT_ID)
    )


@mock_wafv2
def test_list_web_ac_ls():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()

    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("John", "REGIONAL"),
    )
    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("JohnSon", "REGIONAL"),
    )
    test_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("Sarah", "CLOUDFRONT"),
    )
    res = test_client.post(
        "/", headers=LIST_WEB_ACL_HEADERS, json=LIST_WEB_ACL_BODY("REGIONAL")
    )
    assert res.status_code == 200

    web_acls = res.json["WebACLs"]
    assert len(web_acls) == 2
    assert web_acls[0]["Name"] == "John"
    assert web_acls[1]["Name"] == "JohnSon"

    res = test_client.post(
        "/", headers=LIST_WEB_ACL_HEADERS, json=LIST_WEB_ACL_BODY("CLOUDFRONT")
    )
    assert res.status_code == 200
    web_acls = res.json["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Sarah"


@mock_ec2
@mock_elbv2
@mock_wafv2
def test_associate_web_acl():

    wafv2_backend = server.create_backend_app("wafv2")
    wafv2_client = wafv2_backend.test_client()
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")
    ec2_client = boto3.resource("ec2", region_name="us-east-1")
    resource_arn = create_alb(elbv2_client, ec2_client)
    wacl_arn = wafv2_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("test_wacl_name", "REGIONAL"),
    ).json["Summary"]["ARN"]

    # Associate wacl with alb
    res = wafv2_client.post(
        "/",
        headers=ASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_ASSOCIATE_WEB_ACL_BODY(wacl_arn, resource_arn),
    )
    assert res.status_code == 200

    # Try with invalid arns to see if WAFNonexistentItemException error is raised
    res = wafv2_client.post(
        "/",
        headers=ASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_ASSOCIATE_WEB_ACL_BODY(
            "i_am_an_invalid_arn_this_should_raise_error", resource_arn
        ),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because your resource does not exist."
        in res.data
    )
    assert b"WAFNonexistentItem" in res.data

    res = wafv2_client.post(
        "/",
        headers=ASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_ASSOCIATE_WEB_ACL_BODY(
            wacl_arn, "i_am_an_invalid_arn_this_should_raise_error"
        ),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because your resource does not exist."
        in res.data
    )
    assert b"WAFNonexistentItem" in res.data


@mock_ec2
@mock_elbv2
@mock_wafv2
def test_disassociate_web_acl():

    wafv2_backend = server.create_backend_app("wafv2")
    wafv2_client = wafv2_backend.test_client()
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")
    ec2_client = boto3.resource("ec2", region_name="us-east-1")
    resource_arn = create_alb(elbv2_client, ec2_client)
    wacl_arn = wafv2_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("test_wacl_name", "REGIONAL"),
    ).json["Summary"]["ARN"]

    # Associate the wacl
    res = wafv2_client.post(
        "/",
        headers=ASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_ASSOCIATE_WEB_ACL_BODY(wacl_arn, resource_arn),
    )
    assert res.status_code == 200

    # Disassociate it
    res = wafv2_client.post(
        "/",
        headers=DISASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_DISASSOCIATE_WEB_ACL_BODY(resource_arn),
    )
    assert res.status_code == 200

    # Delete ALB and disassociate it again - should raise error since ARN doesn't exist
    elbv2_client.delete_load_balancer(LoadBalancerArn=resource_arn)
    res = wafv2_client.post(
        "/",
        headers=DISASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_DISASSOCIATE_WEB_ACL_BODY(resource_arn),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because your resource does not exist."
        in res.data
    )
    assert b"WAFNonexistentItem" in res.data


@mock_ec2
@mock_elbv2
@mock_wafv2
def test_get_web_acl_for_resource():

    wafv2_backend = server.create_backend_app("wafv2")
    wafv2_client = wafv2_backend.test_client()
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")
    ec2_client = boto3.resource("ec2", region_name="us-east-1")
    resource_arn = create_alb(elbv2_client, ec2_client)
    wacl_arn = wafv2_client.post(
        "/",
        headers=CREATE_WEB_ACL_HEADERS,
        json=CREATE_WEB_ACL_BODY("test_wacl_name", "REGIONAL"),
    ).json["Summary"]["ARN"]

    # Associate the wacl
    res = wafv2_client.post(
        "/",
        headers=ASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_ASSOCIATE_WEB_ACL_BODY(wacl_arn, resource_arn),
    )
    assert res.status_code == 200

    # Verify correct wacl is associated with resource (alb)
    res = wafv2_client.post(
        "/",
        headers=GET_WEB_ACL_FOR_RESOURCE_HEADERS,
        json=CREATE_GET_WEB_ACL_FOR_RESOURCE_BODY(resource_arn),
    )
    assert res.status_code == 200
    web_acl = res.json["WebACL"]
    assert web_acl.get("ARN") == wacl_arn

    # Disassociate wacl and verify wacl is no longer associated with resource (alb)
    res = wafv2_client.post(
        "/",
        headers=DISASSOCIATE_WEB_ACL_HEADERS,
        json=CREATE_DISASSOCIATE_WEB_ACL_BODY(resource_arn),
    )
    assert res.status_code == 200
    res = wafv2_client.post(
        "/",
        headers=GET_WEB_ACL_FOR_RESOURCE_HEADERS,
        json=CREATE_GET_WEB_ACL_FOR_RESOURCE_BODY(resource_arn),
    )
    assert res.status_code == 200
    assert len(res.json) == 0

    # Try with non existent resource_arn (delete the resource so it's ARN should now not exist)
    elbv2_client.delete_load_balancer(LoadBalancerArn=resource_arn)
    res = wafv2_client.post(
        "/",
        headers=GET_WEB_ACL_FOR_RESOURCE_HEADERS,
        json=CREATE_GET_WEB_ACL_FOR_RESOURCE_BODY(resource_arn),
    )
    assert res.status_code == 400
    assert (
        b"AWS WAF could not perform the operation because your resource does not exist."
        in res.data
    )
    assert b"WAFNonexistentItem" in res.data
