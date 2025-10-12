from moto.cloudformation.parsing import get_references_from_template


class TestParametersFromResource:
    def test_no_properties(self):
        template = {"Type": "AWS::S3::Bucket"}
        assert get_references_from_template(template) == []

    def test_properties_without_param(self):
        template = {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "mybucket"}}
        assert get_references_from_template(template) == []

    def test_properties_with_param(self):
        template = {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": {"Ref": "BucketName"},
                "Tags": [{"Key": {"Ref": "KeyName"}, "Value": {"Ref": "KeyDesc"}}],
            },
        }
        assert get_references_from_template(template) == [
            "BucketName",
            "KeyName",
            "KeyDesc",
        ]

    def test_nested_properties_with_param(self):
        template = {
            "Type": "AWS::S3::Bucket",
            "Properties": {"L1": {"L2": {"Ref": "Name"}}},
        }
        assert get_references_from_template(template) == ["Name"]
