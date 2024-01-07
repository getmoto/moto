import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests.test_apigateway.test_apigateway_stage import create_method_integration

from .test_helper_functions import CREATE_WEB_ACL_BODY


@mock_aws
def test_associate_with_unknown_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl_arn = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))[
        "Summary"
    ]["ARN"]

    # We do not have any validation yet on the existence or format of the resource arn
    conn.associate_web_acl(
        WebACLArn=wacl_arn,
        ResourceArn="arn:aws:apigateway:us-east-1::/restapis/unknown/stages/unknown",
    )
    conn.associate_web_acl(WebACLArn=wacl_arn, ResourceArn="unknownarnwithminlength20")

    # We can validate if the WebACL exists
    with pytest.raises(ClientError) as exc:
        conn.associate_web_acl(
            WebACLArn=f"{wacl_arn}2", ResourceArn="unknownarnwithminlength20"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "WAFNonexistentItemException"
    assert err["Message"] == (
        "AWS WAF couldn’t perform the operation because your resource doesn’t exist."
    )


@mock_aws
def test_associate_with_apigateway_stage():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl_arn = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))[
        "Summary"
    ]["ARN"]

    apigw = boto3.client("apigateway", region_name="us-east-1")
    api_id, stage_arn = create_apigateway_stage(client=apigw)

    conn.associate_web_acl(WebACLArn=wacl_arn, ResourceArn=stage_arn)

    stage = apigw.get_stage(restApiId=api_id, stageName="test")
    assert stage["webAclArn"] == wacl_arn

    conn.disassociate_web_acl(ResourceArn=stage_arn)

    stage = apigw.get_stage(restApiId=api_id, stageName="test")
    assert "webAclArn" not in stage


@mock_aws
def test_get_web_acl_for_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    wacl_arn = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))[
        "Summary"
    ]["ARN"]

    apigw = boto3.client("apigateway", region_name="us-east-1")
    _, stage_arn = create_apigateway_stage(client=apigw)

    resp = conn.get_web_acl_for_resource(ResourceArn=stage_arn)
    assert "WebACL" not in resp

    conn.associate_web_acl(WebACLArn=wacl_arn, ResourceArn=stage_arn)

    resp = conn.get_web_acl_for_resource(ResourceArn=stage_arn)
    assert "WebACL" in resp
    assert resp["WebACL"]["Name"] == "John"
    assert resp["WebACL"]["ARN"] == wacl_arn


@mock_aws
def test_disassociate_unknown_resource():
    conn = boto3.client("wafv2", region_name="us-east-1")
    # Nothing happens
    conn.disassociate_web_acl(ResourceArn="unknownarnwithlength20")


def create_apigateway_stage(client):
    stage_name = "staging"
    response = client.create_rest_api(name="my_api", description="this")
    api_id = response["id"]

    create_method_integration(client=client, api_id=api_id)
    response = client.create_deployment(restApiId=api_id, stageName=stage_name)
    deployment_id = response["id"]

    client.create_stage(restApiId=api_id, stageName="test", deploymentId=deployment_id)
    stage_arn = f"arn:aws:apigateway:us-east-1::/restapis/{api_id}/stages/test"
    return api_id, stage_arn
