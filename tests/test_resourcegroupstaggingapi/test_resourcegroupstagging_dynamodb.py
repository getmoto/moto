import unittest

import boto3

from moto import mock_aws


@mock_aws
class TestDynamoDBTagging(unittest.TestCase):
    def setUp(self) -> None:
        self.dynamodb = boto3.client("dynamodb", region_name="us-west-2")
        self.rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
        self.resources_tagged = []
        self.resources_untagged = []
        for i in range(3):
            table = self.dynamodb.create_table(
                AttributeDefinitions=[{"AttributeName": "col", "AttributeType": "S"}],
                TableName=f"table-{i}",
                KeySchema=[{"AttributeName": "col", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
            ).get("TableDescription")
            self.dynamodb.tag_resource(
                ResourceArn=table["TableArn"],
                Tags=[{"Key": "test", "Value": f"value-{i}"}] if i else [],
            )
            group = self.resources_tagged if i else self.resources_untagged
            group.append(table["TableArn"])

    def test_get_resources_dynamodb(self):
        def assert_response(response, expected_count, resource_type=None):
            results = response.get("ResourceTagMappingList", [])
            assert len(results) == expected_count
            for item in results:
                arn = item["ResourceARN"]
                assert arn in self.resources_tagged
                assert arn not in self.resources_untagged
                if resource_type:
                    assert f":{resource_type}:" in arn

        resp = self.rtapi.get_resources(ResourceTypeFilters=["dynamodb"])
        assert_response(resp, 2)
        resp = self.rtapi.get_resources(ResourceTypeFilters=["dynamodb:table"])
        assert_response(resp, 2)
        resp = self.rtapi.get_resources(
            TagFilters=[{"Key": "test", "Values": ["value-1"]}]
        )
        assert_response(resp, 1)

    def test_tag_resources_dynamodb(self):
        # WHEN
        # we tag resources
        self.rtapi.tag_resources(
            ResourceARNList=self.resources_tagged,
            Tags={"key1": "value1", "key2": "value2"},
        )

        # THEN
        # we can retrieve the tags using the DynamoDB API
        def get_tags(arn):
            return self.dynamodb.list_tags_of_resource(ResourceArn=arn)["Tags"]

        for arn in self.resources_tagged:
            assert {"Key": "key1", "Value": "value1"} in get_tags(arn)
            assert {"Key": "key2", "Value": "value2"} in get_tags(arn)
        for arn in self.resources_untagged:
            assert get_tags(arn) == []
