import unittest

from moto.utilities.tagging_service import TaggingService


class TestTaggingService(unittest.TestCase):
    def test_list_empty(self):
        svc = TaggingService()
        result = svc.list_tags_for_resource("test")
        self.assertEqual(result, {"Tags": []})

    def test_create_tag(self):
        svc = TaggingService("TheTags", "TagKey", "TagValue")
        tags = [{"TagKey": "key_key", "TagValue": "value_value"}]
        svc.tag_resource("arn", tags)
        actual = svc.list_tags_for_resource("arn")
        expected = {"TheTags": [{"TagKey": "key_key", "TagValue": "value_value"}]}
        self.assertDictEqual(expected, actual)

    def test_create_tag_without_value(self):
        svc = TaggingService()
        tags = [{"Key": "key_key"}]
        svc.tag_resource("arn", tags)
        actual = svc.list_tags_for_resource("arn")
        expected = {"Tags": [{"Key": "key_key", "Value": None}]}
        self.assertDictEqual(expected, actual)

    def test_delete_tag_using_names(self):
        svc = TaggingService()
        tags = [{"Key": "key_key", "Value": "value_value"}]
        svc.tag_resource("arn", tags)
        svc.untag_resource_using_names("arn", ["key_key"])
        result = svc.list_tags_for_resource("arn")
        self.assertEqual(result, {"Tags": []})

    def test_list_empty_delete(self):
        svc = TaggingService()
        svc.untag_resource_using_names("arn", ["key_key"])
        result = svc.list_tags_for_resource("arn")
        self.assertEqual(result, {"Tags": []})

    def test_delete_tag_using_tags(self):
        svc = TaggingService()
        tags = [{"Key": "key_key", "Value": "value_value"}]
        svc.tag_resource("arn", tags)
        svc.untag_resource_using_tags("arn", tags)
        result = svc.list_tags_for_resource("arn")
        self.assertEqual(result, {"Tags": []})

    def test_extract_tag_names(self):
        svc = TaggingService()
        tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
        actual = svc.extract_tag_names(tags)
        expected = ["key1", "key2"]
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
