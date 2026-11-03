"""Handles incoming bedrock requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import BedrockBackend, bedrock_backends


class BedrockResponse(BaseResponse):
    """Handler for Bedrock requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="bedrock")
        self.automated_parameter_parsing = True

    @property
    def bedrock_backend(self) -> BedrockBackend:
        """Return backend instance specific for this region."""
        return bedrock_backends[self.current_account][self.region]

    def create_model_customization_job(self) -> str:
        job_name = self._get_param("jobName")
        custom_model_name = self._get_param("customModelName")
        role_arn = self._get_param("roleArn")
        client_request_token = self._get_param("clientRequestToken")
        base_model_identifier = self._get_param("baseModelIdentifier")
        customization_type = self._get_param("customizationType")
        custom_model_kms_key_id = self._get_param("customModelKmsKeyId")
        job_tags = self._get_param("jobTags")
        custom_model_tags = self._get_param("customModelTags")
        training_data_config = self._get_param("trainingDataConfig")
        validation_data_config = self._get_param("validationDataConfig")
        output_data_config = self._get_param("outputDataConfig")
        hyper_parameters = self._get_param("hyperParameters")
        vpc_config = self._get_param("vpcConfig")
        job_arn = self.bedrock_backend.create_model_customization_job(
            job_name=job_name,
            custom_model_name=custom_model_name,
            role_arn=role_arn,
            client_request_token=client_request_token,
            base_model_identifier=base_model_identifier,
            customization_type=customization_type,
            custom_model_kms_key_id=custom_model_kms_key_id,
            job_tags=job_tags,
            custom_model_tags=custom_model_tags,
            training_data_config=training_data_config,
            validation_data_config=validation_data_config,
            output_data_config=output_data_config,
            hyper_parameters=hyper_parameters,
            vpc_config=vpc_config,
        )
        return json.dumps({"jobArn": job_arn})

    def get_model_customization_job(self) -> str:
        job_identifier = self._get_param("jobIdentifier")
        model_customization_job = self.bedrock_backend.get_model_customization_job(
            job_identifier=job_identifier
        )
        return json.dumps(dict(model_customization_job.to_dict()))

    def get_model_invocation_logging_configuration(self) -> str:
        logging_config = (
            self.bedrock_backend.get_model_invocation_logging_configuration()
        )
        return json.dumps({"loggingConfig": logging_config})

    def put_model_invocation_logging_configuration(self) -> None:
        logging_config = self._get_param("loggingConfig")
        self.bedrock_backend.put_model_invocation_logging_configuration(
            logging_config=logging_config
        )
        return

    def tag_resource(self) -> None:
        resource_arn = self._get_param("resourceARN")
        tags = self._get_param("tags")
        self.bedrock_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return

    def untag_resource(self) -> str:
        resource_arn = self._get_param("resourceARN")
        tag_keys = self._get_param("tagKeys")
        self.bedrock_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return json.dumps({})

    def list_tags_for_resource(self) -> str:
        resource_arn = self._get_param("resourceARN")
        tags = self.bedrock_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return json.dumps({"tags": tags})

    def get_custom_model(self) -> str:
        model_identifier = self._get_param("modelIdentifier")
        custom_model = self.bedrock_backend.get_custom_model(
            model_identifier=model_identifier
        )
        return json.dumps(dict(custom_model.to_dict()))

    def list_custom_models(self) -> str:
        creation_time_before = self._get_param("creationTimeBefore")
        creation_time_after = self._get_param("creationTimeAfter")
        name_contains = self._get_param("nameContains")
        base_model_arn_equals = self._get_param("baseModelArnEquals")
        foundation_model_arn_equals = self._get_param("foundationModelArnEquals")
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        sort_by = self._get_param("sortBy")
        sort_order = self._get_param("sortOrder")

        model_summaries, next_token = self.bedrock_backend.list_custom_models(
            creation_time_before=creation_time_before,
            creation_time_after=creation_time_after,
            name_contains=name_contains,
            base_model_arn_equals=base_model_arn_equals,
            foundation_model_arn_equals=foundation_model_arn_equals,
            max_results=max_results,
            next_token=next_token,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        summaries = [
            {
                "modelArn": model.model_arn,
                "modelName": model.model_name,
                "creationTime": model.creation_time,
                "baseModelArn": model.base_model_arn,
                "baseModelName": model.base_model_name,
                "jobArn": model.job_arn,
                "customizationType": model.customization_type,
            }
            for model in model_summaries
        ]
        return json.dumps({"nextToken": next_token, "modelSummaries": summaries})

    def list_model_customization_jobs(self) -> str:
        creation_time_after = self._get_param("creationTimeAfter")
        creation_time_before = self._get_param("creationTimeBefore")
        status_equals = self._get_param("statusEquals")
        name_contains = self._get_param("nameContains")
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        sort_by = self._get_param("sortBy")
        sort_order = self._get_param("sortOrder")

        jobs, next_token = self.bedrock_backend.list_model_customization_jobs(
            creation_time_after=creation_time_after,
            creation_time_before=creation_time_before,
            status_equals=status_equals,
            name_contains=name_contains,
            max_results=max_results,
            next_token=next_token,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        job_summaries = [
            {
                "jobArn": job.job_arn,
                "baseModelArn": job.base_model_arn,
                "jobName": job.job_name,
                "status": job.status,
                "lastModifiedTime": job.last_modified_time,
                "creationTime": job.creation_time,
                "endTime": job.end_time,
                "customModelArn": job.output_model_arn,
                "customModelName": job.custom_model_name,
                "customizationType": job.customization_type,
            }
            for job in jobs
        ]
        return json.dumps(
            {
                "nextToken": next_token,
                "modelCustomizationJobSummaries": job_summaries,
            }
        )

    def delete_custom_model(self) -> str:
        model_identifier = self._get_param("modelIdentifier")
        self.bedrock_backend.delete_custom_model(
            model_identifier=model_identifier,
        )
        return json.dumps({})

    def stop_model_customization_job(self) -> str:
        job_identifier = self._get_param("jobIdentifier")
        self.bedrock_backend.stop_model_customization_job(
            job_identifier=job_identifier,
        )
        return json.dumps({})

    def delete_model_invocation_logging_configuration(self) -> str:
        self.bedrock_backend.delete_model_invocation_logging_configuration()
        return json.dumps({})
