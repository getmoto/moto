"""Handles incoming comprehend requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import ComprehendBackend, comprehend_backends


class ComprehendResponse(BaseResponse):
    """Handler for Comprehend requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="comprehend")

    @property
    def comprehend_backend(self) -> ComprehendBackend:
        """Return backend instance specific for this region."""
        return comprehend_backends[self.current_account][self.region]

    def list_entity_recognizers(self) -> str:
        params = json.loads(self.body)
        _filter = params.get("Filter", {})
        recognizers = self.comprehend_backend.list_entity_recognizers(_filter=_filter)
        return json.dumps(
            dict(EntityRecognizerPropertiesList=[r.to_dict() for r in recognizers])
        )

    def list_document_classifiers(self) -> str:
        params = json.loads(self.body)
        _filter = params.get("Filter", {})
        classifiers = self.comprehend_backend.list_document_classifiers(_filter=_filter)
        return json.dumps(
            dict(DocumentClassifierPropertiesList=[c.to_dict() for c in classifiers])
        )

    def list_endpoints(self) -> str:
        params = json.loads(self.body)
        _filter = params.get("Filter", {})
        endpoints = self.comprehend_backend.list_endpoints(_filter=_filter)
        return json.dumps(dict(EndpointPropertiesList=[e.to_dict() for e in endpoints]))

    def list_flywheels(self) -> str:
        params = json.loads(self.body)
        _filter = params.get("Filter", {})
        flywheels = self.comprehend_backend.list_flywheels(_filter=_filter)
        return json.dumps(dict(FlywheelPropertiesList=[f.to_dict() for f in flywheels]))

    def create_entity_recognizer(self) -> str:
        params = json.loads(self.body)
        recognizer_name = params.get("RecognizerName")
        version_name = params.get("VersionName")
        data_access_role_arn = params.get("DataAccessRoleArn")
        tags = params.get("Tags")
        input_data_config = params.get("InputDataConfig")
        language_code = params.get("LanguageCode")
        volume_kms_key_id = params.get("VolumeKmsKeyId")
        client_request_token = params.get("ClientRequestToken")
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
            client_request_token=client_request_token,
            model_kms_key_id=model_kms_key_id,
            model_policy=model_policy,
        )
        return json.dumps(dict(EntityRecognizerArn=entity_recognizer_arn))

    def create_document_classifier(self) -> str:
        params = json.loads(self.body)
        document_classifier_name = params.get("DocumentClassifierName")
        data_access_role_arn = params.get("DataAccessRoleArn")
        tags = params.get("Tags")
        input_data_config = params.get("InputDataConfig")
        output_data_config = params.get("OutputDataConfig")
        client_request_token = params.get("ClientRequestToken")
        language_code = params.get("LanguageCode")
        volume_kms_key_id = params.get("VolumeKmsKeyId")
        vpc_config = params.get("VpcConfig")
        mode = params.get("Mode")
        model_kms_key_id = params.get("ModelKmsKeyId")
        model_policy = params.get("ModelPolicy")
        document_classifier_arn = self.comprehend_backend.create_document_classifier(
            document_classifier_name=document_classifier_name,
            data_access_role_arn=data_access_role_arn,
            tags=tags,
            input_data_config=input_data_config,
            output_data_config=output_data_config,
            client_request_token=client_request_token,
            language_code=language_code,
            volume_kms_key_id=volume_kms_key_id,
            vpc_config=vpc_config,
            mode=mode,
            model_kms_key_id=model_kms_key_id,
            model_policy=model_policy,
        )
        return json.dumps(dict(DocumentClassifierArn=document_classifier_arn))

    def create_flywheel(self) -> str:
        params = json.loads(self.body)
        flywheel_name = params.get("FlywheelName")
        active_model_arn = params.get("ActiveModelArn")
        task_config = params.get("TaskConfig")
        data_access_role_arn = params.get("DataAccessRoleArn")
        model_type = params.get("ModelType")
        data_lake_s3_uri = params.get("DataLakeS3Uri")
        data_security_config = params.get("DataSecurityConfig")
        client_request_token = params.get("ClientRequestToken")
        tags = params.get("Tags")
        flywheel_arn = self.comprehend_backend.create_flywheel(
            flywheel_name=flywheel_name,
            active_model_arn=active_model_arn,
            task_config=task_config,
            data_access_role_arn=data_access_role_arn,
            model_type=model_type,
            data_lake_s3_uri=data_lake_s3_uri,
            data_security_config=data_security_config,
            client_request_token=client_request_token,
            tags=tags,
        )
        return json.dumps(dict(FlywheelArn=flywheel_arn))

    def create_endpoint(self) -> str:
        params = json.loads(self.body)
        endpoint_name = params.get("EndpointName")
        model_arn = params.get("ModelArn")
        desired_inference_units = params.get("DesiredInferenceUnits")
        client_request_token = params.get("ClientRequestToken")
        data_access_role_arn = params.get("DataAccessRoleArn")
        flywheel_arn = params.get("FlywheelArn")
        tags = params.get("Tags")
        endpoint_arn = self.comprehend_backend.create_endpoint(
            endpoint_name=endpoint_name,
            model_arn=model_arn,
            desired_inference_units=desired_inference_units,
            client_request_token=client_request_token,
            data_access_role_arn=data_access_role_arn,
            flywheel_arn=flywheel_arn,
            tags=tags,
        )
        return json.dumps(dict(EndpointArn=endpoint_arn))

    def describe_entity_recognizer(self) -> str:
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        recognizer = self.comprehend_backend.describe_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return json.dumps(dict(EntityRecognizerProperties=recognizer.to_dict()))

    def describe_document_classifier(self) -> str:
        params = json.loads(self.body)
        document_classifier_arn = params.get("DocumentClassifierArn")
        classifier = self.comprehend_backend.describe_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )
        return json.dumps(dict(DocumentClassifierProperties=classifier.to_dict()))

    def describe_endpoint(self) -> str:
        params = json.loads(self.body)
        endpoint_arn = params.get("EndpointArn")
        endpoint = self.comprehend_backend.describe_endpoint(
            endpoint_arn=endpoint_arn,
        )
        return json.dumps(dict(EndpointProperties=endpoint.to_dict()))

    def describe_flywheel(self) -> str:
        params = json.loads(self.body)
        flywheel_arn = params.get("FlywheelArn")
        flywheel_iteration_id = params.get("FlywheelIterationId")
        flywheel = self.comprehend_backend.describe_flywheel(
            flywheel_arn=flywheel_arn,
            flywheel_iteration_id=flywheel_iteration_id,
        )
        return json.dumps(dict(FlywheelProperties=flywheel.to_dict()))

    def stop_training_entity_recognizer(self) -> str:
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        self.comprehend_backend.stop_training_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return json.dumps(dict())

    def stop_training_document_classifier(self) -> str:
        params = json.loads(self.body)
        document_classifier_arn = params.get("DocumentClassifierArn")
        self.comprehend_backend.stop_training_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )
        return "{}"

    def update_endpoint(self) -> str:
        params = json.loads(self.body)
        endpoint_arn = params.get("EndpointArn")
        desired_inference_units = params.get("DesiredInferenceUnits")
        desired_model_arn = params.get("DesiredModelArn")
        desired_data_access_role_arn = params.get("DesiredDataAccessRoleArn")
        flywheel_arn = params.get("FlywheelArn")
        self.comprehend_backend.update_endpoint(
            endpoint_arn=endpoint_arn,
            desired_inference_units=desired_inference_units,
            desired_model_arn=desired_model_arn,
            desired_data_access_role_arn=desired_data_access_role_arn,
            flywheel_arn=flywheel_arn,
        )
        return json.dumps(dict(DesiredModelArn=desired_model_arn))

    def start_flywheel_iteration(self) -> str:
        params = json.loads(self.body)
        flywheel_arn = params.get("FlywheelArn")
        client_request_token = params.get("ClientRequestToken")
        self.comprehend_backend.start_flywheel_iteration(
            flywheel_arn=flywheel_arn,
            client_request_token=client_request_token,
        )
        return json.dumps(
            dict(
                FlyWheelArn=flywheel_arn,
                FlyWheelIterationId=params.get("FlywheelIterationId"),
            )
        )

    def list_tags_for_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tags = self.comprehend_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return json.dumps(dict(ResourceArn=resource_arn, Tags=tags))

    def delete_entity_recognizer(self) -> str:
        params = json.loads(self.body)
        entity_recognizer_arn = params.get("EntityRecognizerArn")
        self.comprehend_backend.delete_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return "{}"

    def delete_document_classifier(self) -> str:
        params = json.loads(self.body)
        document_classifier_arn = params.get("DocumentClassifierArn")
        self.comprehend_backend.delete_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )
        return "{}"

    def delete_endpoint(self) -> str:
        params = json.loads(self.body)
        endpoint_arn = params.get("EndpointArn")
        self.comprehend_backend.delete_endpoint(
            endpoint_arn=endpoint_arn,
        )
        return "{}"

    def delete_flywheel(self) -> str:
        params = json.loads(self.body)
        flywheel_arn = params.get("FlywheelArn")
        self.comprehend_backend.delete_flywheel(
            flywheel_arn=flywheel_arn,
        )
        return "{}"

    def tag_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tags = params.get("Tags")
        self.comprehend_backend.tag_resource(resource_arn, tags)
        return "{}"

    def untag_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = params.get("ResourceArn")
        tag_keys = params.get("TagKeys")
        self.comprehend_backend.untag_resource(resource_arn, tag_keys)
        return "{}"

    def detect_pii_entities(self) -> str:
        params = json.loads(self.body)
        text = params.get("Text")
        language = params.get("LanguageCode")
        resp = self.comprehend_backend.detect_pii_entities(text, language)
        return json.dumps(dict(Entities=resp))

    def detect_key_phrases(self) -> str:
        params = json.loads(self.body)
        text = params.get("Text")
        language = params.get("LanguageCode")
        resp = self.comprehend_backend.detect_key_phrases(text, language)
        return json.dumps(dict(KeyPhrases=resp))

    def detect_sentiment(self) -> str:
        params = json.loads(self.body)
        text = params.get("Text")
        language = params.get("LanguageCode")
        resp = self.comprehend_backend.detect_sentiment(text, language)
        return json.dumps(resp)
