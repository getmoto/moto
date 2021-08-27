from __future__ import unicode_literals
import json
import pytest

import sure  # noqa
import boto3
from botocore.exceptions import ClientError
from moto import mock_wafv2
from .test_helper_functions import CREATE_WEB_ACL_BODY, LIST_WEB_ACL_BODY
from moto.core import ACCOUNT_ID


@mock_wafv2
def test_create_web_acl():

    conn = boto3.client("wafv2", region_name="us-east-1")
    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    web_acl = res["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith(
        "arn:aws:wafv2:us-east-1:{}:regional/webacl/John/".format(ACCOUNT_ID)
    )
    # Duplicate name - should raise error
    with pytest.raises(ClientError) as ex:
        conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    err = ex.value.response["Error"]
    err["Message"].should.contain(
        "AWS WAF could not perform the operation because some resource in your request is a duplicate of an existing one."
    )
    err["Code"].should.equal("400")

    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Carl", "CLOUDFRONT"))
    web_acl = res["Summary"]
    assert web_acl.get("ARN").startswith(
        "arn:aws:wafv2:global:{}:global/webacl/Carl/".format(ACCOUNT_ID)
    )


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
