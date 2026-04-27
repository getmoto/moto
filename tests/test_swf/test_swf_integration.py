import boto3

from moto import mock_aws


def _register_and_describe_domain(client, name, tags=None):
    kwargs = {
        "name": name,
        "workflowExecutionRetentionPeriodInDays": "30",
    }
    if tags:
        kwargs["tags"] = tags
    client.register_domain(**kwargs)

    return client.describe_domain(name=name)


@mock_aws
def test_rgtapi_get_resources():
    swf = boto3.client("swf", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    a_arn = _register_and_describe_domain(
        swf, "domain-a", tags=[{"key": "env", "value": "prod"}]
    )["domainInfo"]["arn"]
    b_arn = _register_and_describe_domain(
        swf, "domain-b", tags=[{"key": "env", "value": "dev"}]
    )["domainInfo"]["arn"]
    # domain with no tags should not appear
    c_arn = _register_and_describe_domain(swf, "domain-c")["domainInfo"]["arn"]

    resp = rtapi.get_resources(ResourceTypeFilters=["swf"])
    resources = resp["ResourceTagMappingList"]

    arns = [r["ResourceARN"] for r in resources]
    assert a_arn in arns
    assert b_arn in arns
    assert c_arn not in arns


@mock_aws
def test_rgtapi_get_resources_with_tag_filter():
    swf = boto3.client("swf", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    _register_and_describe_domain(
        swf, "domain-prod", tags=[{"key": "env", "value": "prod"}]
    )
    _register_and_describe_domain(
        swf, "domain-dev", tags=[{"key": "env", "value": "dev"}]
    )

    resp = rtapi.get_resources(
        ResourceTypeFilters=["swf"],
        TagFilters=[{"Key": "env", "Values": ["prod"]}],
    )
    resources = resp["ResourceTagMappingList"]

    assert len(resources) == 1
    assert resources[0]["ResourceARN"].endswith("/domain/domain-prod")
    assert {"Key": "env", "Value": "prod"} in resources[0]["Tags"]


@mock_aws
def test_rgtapi_tag_resources():
    swf = boto3.client("swf", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    domain_arn = _register_and_describe_domain(
        swf, "my-domain", tags=[{"key": "k1", "value": "v1"}]
    )

    rtapi.tag_resources(
        ResourceARNList=[domain_arn],
        Tags={"NewKey": "NewValue"},
    )

    tags = swf.list_tags_for_resource(resourceArn=domain_arn)["tags"]
    assert {"key": "k1", "value": "v1"} in tags
    assert {"key": "NewKey", "value": "NewValue"} in tags


@mock_aws
def test_rgtapi_untag_resources():
    swf = boto3.client("swf", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    domain_arn = _register_and_describe_domain(
        swf,
        "my-domain",
        tags=[{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}],
    )

    rtapi.tag_resources(
        ResourceARNList=[domain_arn],
        Tags={"NewKey": "NewValue"},
    )

    rtapi.untag_resources(
        ResourceARNList=[domain_arn],
        TagKeys=["k1", "k2"],
    )

    tags = swf.list_tags_for_resource(resourceArn=domain_arn)["tags"]
    assert {"key": "k1", "value": "v1"} not in tags
    assert {"key": "k2", "value": "v2"} not in tags
    assert {"key": "NewKey", "value": "NewValue"} in tags
