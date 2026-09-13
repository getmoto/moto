import boto3

from moto import mock_aws

from . import cloudfront_test_scaffolding as scaffold


@mock_aws
def test_rgtapi_get_tag_values():
    client = boto3.client("cloudfront", "us-east-1")

    for i in range(1, 3):
        caller_reference = f"distribution{i}"
        client.create_distribution_with_tags(
            DistributionConfigWithTags=scaffold.example_dist_config_with_tags(
                caller_reference
            )
        )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["cloudfront"],
        TagFilters=[{"Key": "k1", "Values": ["v1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 2
    assert {"Key": "k1", "Value": "v1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_rgtapi_tag_resources():
    client = boto3.client("cloudfront", "us-east-1")
    dist = client.create_distribution_with_tags(
        DistributionConfigWithTags=scaffold.example_dist_config_with_tags("ref")
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")
    dist_arn = dist["Distribution"]["ARN"]

    rtapi.tag_resources(
        ResourceARNList=[dist_arn],
        Tags={"NewKey": "NewValue"},
    )

    tags = client.list_tags_for_resource(Resource=dist_arn)["Tags"]["Items"]

    assert {"Key": "k1", "Value": "v1"} in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags


@mock_aws
def test_rgtapi_untag_resources():
    client = boto3.client("cloudfront", "us-east-1")

    dist = client.create_distribution_with_tags(
        DistributionConfigWithTags=scaffold.example_dist_config_with_tags("ref")
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")
    dist_arn = dist["Distribution"]["ARN"]

    rtapi.tag_resources(
        ResourceARNList=[dist_arn],
        Tags={"NewKey": "NewValue"},
    )

    rtapi.untag_resources(
        ResourceARNList=[dist_arn],
        TagKeys=["k1", "k2"],
    )

    tags = client.list_tags_for_resource(Resource=dist_arn)["Tags"]["Items"]

    assert {"Key": "k1", "Value": "v1"} not in tags
    assert {"Key": "k2", "Value": "v2"} not in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags


@mock_aws
def test_rgtapi_get_resources_by_type():
    client = boto3.client("cloudfront", "us-east-1")

    client.create_distribution_with_tags(
        DistributionConfigWithTags=scaffold.example_dist_config_with_tags("ref")
    )
    function = client.create_function(
        Name="test-function",
        FunctionConfig={"Comment": "Test function", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=b"function handler(event) { return event; }",
        Tags={"Items": [{"Key": "k1", "Value": "v1"}]},
    )["FunctionSummary"]
    function_arn = function["FunctionMetadata"]["FunctionARN"]
    kv_store = client.create_key_value_store(
        Name="test-store",
        Comment="Test key value store",
        Tags={"Items": [{"Key": "k1", "Value": "v1"}]},
    )["KeyValueStore"]

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    resp = rtapi.get_resources(ResourceTypeFilters=["cloudfront:function"])
    assert [r["ResourceARN"] for r in resp["ResourceTagMappingList"]] == [function_arn]
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "k1", "Value": "v1"}]

    resp = rtapi.get_resources(ResourceTypeFilters=["cloudfront:key-value-store"])
    assert [r["ResourceARN"] for r in resp["ResourceTagMappingList"]] == [
        kv_store["ARN"]
    ]
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "k1", "Value": "v1"}]

    # Filtering on the service returns every resource type
    resp = rtapi.get_resources(ResourceTypeFilters=["cloudfront"])
    arns = {r["ResourceARN"] for r in resp["ResourceTagMappingList"]}
    assert function_arn in arns
    assert kv_store["ARN"] in arns
    assert len(arns) == 3


@mock_aws
def test_rgtapi_get_resources_by_tag_for_function_and_key_value_store():
    client = boto3.client("cloudfront", "us-east-1")

    function_arn = client.create_function(
        Name="test-function",
        FunctionConfig={"Comment": "Test function", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=b"function handler(event) { return event; }",
        Tags={"Items": [{"Key": "Environment", "Value": "Test"}]},
    )["FunctionSummary"]["FunctionMetadata"]["FunctionARN"]
    kv_store = client.create_key_value_store(
        Name="test-store",
        Comment="Test key value store",
        Tags={"Items": [{"Key": "Environment", "Value": "Prod"}]},
    )["KeyValueStore"]

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    resp = rtapi.get_resources(
        TagFilters=[{"Key": "Environment", "Values": ["Test"]}],
    )
    assert [r["ResourceARN"] for r in resp["ResourceTagMappingList"]] == [function_arn]

    resp = rtapi.get_resources(
        TagFilters=[{"Key": "Environment", "Values": ["Prod"]}],
    )
    assert [r["ResourceARN"] for r in resp["ResourceTagMappingList"]] == [
        kv_store["ARN"]
    ]

    # A key-only filter matches any value
    resp = rtapi.get_resources(TagFilters=[{"Key": "Environment"}])
    assert {r["ResourceARN"] for r in resp["ResourceTagMappingList"]} == {
        function_arn,
        kv_store["ARN"],
    }

    # Resources without any tags are never returned
    client.create_function(
        Name="untagged-function",
        FunctionConfig={"Comment": "Untagged", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=b"function handler(event) { return event; }",
    )
    resp = rtapi.get_resources(ResourceTypeFilters=["cloudfront:function"])
    assert [r["ResourceARN"] for r in resp["ResourceTagMappingList"]] == [function_arn]


@mock_aws
def test_rgtapi_tag_and_untag_function():
    client = boto3.client("cloudfront", "us-east-1")

    function_arn = client.create_function(
        Name="test-function",
        FunctionConfig={"Comment": "Test function", "Runtime": "cloudfront-js-1.0"},
        FunctionCode=b"function handler(event) { return event; }",
        Tags={"Items": [{"Key": "k1", "Value": "v1"}]},
    )["FunctionSummary"]["FunctionMetadata"]["FunctionARN"]

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    rtapi.tag_resources(ResourceARNList=[function_arn], Tags={"NewKey": "NewValue"})

    tags = client.list_tags_for_resource(Resource=function_arn)["Tags"]["Items"]
    assert {"Key": "k1", "Value": "v1"} in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags

    rtapi.untag_resources(ResourceARNList=[function_arn], TagKeys=["k1"])

    tags = client.list_tags_for_resource(Resource=function_arn)["Tags"]["Items"]
    assert tags == [{"Key": "NewKey", "Value": "NewValue"}]


@mock_aws
def test_rgtapi_tag_and_untag_key_value_store():
    client = boto3.client("cloudfront", "us-east-1")

    kv_store = client.create_key_value_store(
        Name="test-store",
        Comment="Test key value store",
        Tags={"Items": [{"Key": "k1", "Value": "v1"}]},
    )["KeyValueStore"]
    kv_store_arn = kv_store["ARN"]

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    rtapi.tag_resources(ResourceARNList=[kv_store_arn], Tags={"NewKey": "NewValue"})

    tags = client.list_tags_for_resource(Resource=kv_store_arn)["Tags"]["Items"]
    assert {"Key": "k1", "Value": "v1"} in tags
    assert {"Key": "NewKey", "Value": "NewValue"} in tags

    rtapi.untag_resources(ResourceARNList=[kv_store_arn], TagKeys=["k1"])

    tags = client.list_tags_for_resource(Resource=kv_store_arn)["Tags"]["Items"]
    assert tags == [{"Key": "NewKey", "Value": "NewValue"}]
