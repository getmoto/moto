"""Handles incoming comprehend requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import comprehend_backends


class ComprehendResponse(BaseResponse):
    """Handler for Comprehend requests and responses."""

    def __init__(self):
        super().__init__(service_name="comprehend")

    @property
    def comprehend_backend(self):
        """Return backend instance specific for this region."""
        return comprehend_backends[self.current_account][self.region]

    def list_entity_recognizers(self):
        params = json.loads(self.body)
        _filter = params.get("Filter", {})
        recognizers = self.comprehend_backend.list_entity_recognizers(_filter=_filter)
        return json.dumps(
            dict(EntityRecognizerPropertiesList=[r.to_dict() for r in recognizers])
        )

    def create_entity_recognizer(self):
        params = json.loads(self.body)
        recognizer_name = params.get("RecognizerName")
        version_name = params.get("VersionName")
        data_access_role_arn = params.get("DataAccessRoleArn")
        tags = params.get("Tags")
        input_data_config = params.get("InputDataConfig")
        language_code = params.get("LanguageCode")
        volume_kms_key_id = params.get("VolumeKmsKeyId")
        vpc_config = params.get("VpcConfig")
        model_kms_key_id = params.get("ModelKmsKeyId")
        model_policy = params.get("ModelPolicy")
        entity_recognizer_arn = self.comprehend_backend.create_entity_recognizer(
            recognizer_name=recognizer_name,
            version_name=version_name,
            data_access_role_arn=data_access_role_arn,
            tags=tags,
            input_data_config=input_data_config,
            language_code=language_code,
            volume_kms_key_id=volume_kms_key_id,
            vpc_config=vpc_config,
            model_kms_key_id=model_kms_key_id,
            model_policy=model_policy,
        )
        return json.dumps(dict(EntityRecognizerArn=entity_recognizer_arn))

    def describe_entity_recognizer(self):
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        recognizer = self.comprehend_backend.describe_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return json.dumps(dict(EntityRecognizerProperties=recognizer.to_dict()))

    def stop_training_entity_recognizer(self):
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        self.comprehend_backend.stop_training_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return json.dumps(dict())

    def list_tags_for_resource(self):
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tags = self.comprehend_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return json.dumps(dict(ResourceArn=resource_arn, Tags=tags))

    def delete_entity_recognizer(self):
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        self.comprehend_backend.delete_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return "{}"

    def tag_resource(self):
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tags = params.get("Tags")
        self.comprehend_backend.tag_resource(resource_arn, tags)
        return "{}"

    def untag_resource(self):
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tag_keys = params.get("TagKeys")
        self.comprehend_backend.untag_resource(resource_arn, tag_keys)
        return "{}"
