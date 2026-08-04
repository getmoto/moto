import boto3

from moto import mock_aws


@mock_aws
def test_get_tags_returns_stage_tags():
    client = boto3.client("apigateway", region_name="us-east-1")
    api_id = client.create_rest_api(name="my-api")["id"]
    root_id = client.get_resources(restApiId=api_id)["items"][0]["id"]
    client.put_method(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", authorizationType="NONE"
    )
    client.put_integration(
        restApiId=api_id, resourceId=root_id, httpMethod="GET", type="MOCK"
    )
    client.create_deployment(restApiId=api_id, stageName="dev")
    deployment_id = client.get_deployments(restApiId=api_id)["items"][0]["id"]
    client.create_stage(
        restApiId=api_id,
        stageName="test",
        deploymentId=deployment_id,
        tags={"env": "prod", "team": "backend"},
    )
    arn = f"arn:aws:apigateway:us-east-1::/restapis/{api_id}/stages/test"
    resp = client.get_tags(resourceArn=arn)
    assert resp["tags"] == {"env": "prod", "team": "backend"}
