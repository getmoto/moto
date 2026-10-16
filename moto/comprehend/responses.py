"""Handles incoming comprehend requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import ComprehendBackend, comprehend_backends


class ComprehendResponse(BaseResponse):
    """Handler for Comprehend requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="comprehend")
        self.automated_parameter_parsing = True

    @property
    def comprehend_backend(self) -> ComprehendBackend:
        """Return backend instance specific for this region."""
        return comprehend_backends[self.current_account][self.region]

    def list_entity_recognizers(self) -> ActionResult:
        _filter = self._get_param("Filter", {})
        recognizers = self.comprehend_backend.list_entity_recognizers(_filter=_filter)
        return ActionResult(
            {"EntityRecognizerPropertiesList": [r.to_dict() for r in recognizers]}
        )

    def create_entity_recognizer(self) -> ActionResult:
        recognizer_name = self._get_param("RecognizerName")
        version_name = self._get_param("VersionName")
        data_access_role_arn = self._get_param("DataAccessRoleArn")
        tags = self._get_param("Tags")
        input_data_config = self._get_param("InputDataConfig")
        language_code = self._get_param("LanguageCode")
        volume_kms_key_id = self._get_param("VolumeKmsKeyId")
        vpc_config = self._get_param("VpcConfig")
        model_kms_key_id = self._get_param("ModelKmsKeyId")
        model_policy = self._get_param("ModelPolicy")
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
        return ActionResult({"EntityRecognizerArn": entity_recognizer_arn})

    def describe_entity_recognizer(self) -> ActionResult:
        entity_recognizer_arn = self._get_param("EntityRecognizerArn")
        recognizer = self.comprehend_backend.describe_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return ActionResult({"EntityRecognizerProperties": recognizer.to_dict()})

    def stop_training_entity_recognizer(self) -> ActionResult:
        entity_recognizer_arn = self._get_param("EntityRecognizerArn")
        self.comprehend_backend.stop_training_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self.comprehend_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return ActionResult({"ResourceArn": resource_arn, "Tags": tags})

    def delete_entity_recognizer(self) -> ActionResult:
        entity_recognizer_arn = self._get_param("EntityRecognizerArn")
        self.comprehend_backend.delete_entity_recognizer(
            entity_recognizer_arn=entity_recognizer_arn,
        )
        return EmptyResult()

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags") or []
        tags = {tag["Key"]: tag["Value"] for tag in tags}
        self.comprehend_backend.tag_resource(resource_arn, tags)
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys") or []
        self.comprehend_backend.untag_resource(resource_arn, tag_keys)
        return EmptyResult()

    def detect_pii_entities(self) -> ActionResult:
        text = self._get_param("Text")
        language = self._get_param("LanguageCode")
        resp = self.comprehend_backend.detect_pii_entities(text, language)
        return ActionResult({"Entities": resp})

    def detect_key_phrases(self) -> ActionResult:
        text = self._get_param("Text")
        language = self._get_param("LanguageCode")
        resp = self.comprehend_backend.detect_key_phrases(text, language)
        return ActionResult({"KeyPhrases": resp})

    def detect_sentiment(self) -> ActionResult:
        text = self._get_param("Text")
        language = self._get_param("LanguageCode")
        resp = self.comprehend_backend.detect_sentiment(text, language)
        return ActionResult(resp)

    def create_document_classifier(self) -> ActionResult:
        document_classifier_name = self._get_param("DocumentClassifierName")
        version_name = self._get_param("VersionName")
        data_access_role_arn = self._get_param("DataAccessRoleArn")
        tags = self._get_param("Tags")
        input_data_config = self._get_param("InputDataConfig")
        output_data_config = self._get_param("OutputDataConfig")
        client_request_token = self._get_param("ClientRequestToken")
        language_code = self._get_param("LanguageCode")
        volume_kms_key_id = self._get_param("VolumeKmsKeyId")
        vpc_config = self._get_param("VpcConfig")
        mode = self._get_param("Mode")
        model_kms_key_id = self._get_param("ModelKmsKeyId")
        model_policy = self._get_param("ModelPolicy")

        document_classifier_arn = self.comprehend_backend.create_document_classifier(
            document_classifier_name=document_classifier_name,
            version_name=version_name,
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

        return ActionResult({"DocumentClassifierArn": document_classifier_arn})

    def create_endpoint(self) -> ActionResult:
        endpoint_name = self._get_param("EndpointName")
        model_arn = self._get_param("ModelArn")
        desired_inference_units = self._get_param("DesiredInferenceUnits")
        client_request_token = self._get_param("ClientRequestToken")
        tags = self._get_param("Tags")
        data_access_role_arn = self._get_param("DataAccessRoleArn")
        flywheel_arn = self._get_param("FlywheelArn")
        endpoint_arn, model_arn = self.comprehend_backend.create_endpoint(
            endpoint_name=endpoint_name,
            model_arn=model_arn,
            desired_inference_units=desired_inference_units,
            client_request_token=client_request_token,
            tags=tags,
            data_access_role_arn=data_access_role_arn,
            flywheel_arn=flywheel_arn,
        )

        return ActionResult({"EndpointArn": endpoint_arn, "ModelArn": model_arn})

    def create_flywheel(self) -> ActionResult:
        flywheel_name = self._get_param("FlywheelName")
        active_model_arn = self._get_param("ActiveModelArn")
        data_access_role_arn = self._get_param("DataAccessRoleArn")
        task_config = self._get_param("TaskConfig")
        model_type = self._get_param("ModelType")
        data_lake_s3_uri = self._get_param("DataLakeS3Uri")
        data_security_config = self._get_param("DataSecurityConfig")
        client_request_token = self._get_param("ClientRequestToken")
        tags = self._get_param("Tags")
        flywheel_arn, active_model_arn = self.comprehend_backend.create_flywheel(
            flywheel_name=flywheel_name,
            active_model_arn=active_model_arn,
            data_access_role_arn=data_access_role_arn,
            task_config=task_config,
            model_type=model_type,
            data_lake_s3_uri=data_lake_s3_uri,
            data_security_config=data_security_config,
            client_request_token=client_request_token,
            tags=tags,
        )

        return ActionResult(
            {"FlywheelArn": flywheel_arn, "activeModelArn": active_model_arn}
        )

    def describe_document_classifier(self) -> ActionResult:
        document_classifier_arn = self._get_param("DocumentClassifierArn")
        document_classifier = self.comprehend_backend.describe_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )

        return ActionResult(
            {"DocumentClassifierProperties": document_classifier.to_dict()}
        )

    def describe_endpoint(self) -> ActionResult:
        endpoint_arn = self._get_param("EndpointArn")
        endpoint_properties = self.comprehend_backend.describe_endpoint(
            endpoint_arn=endpoint_arn,
        )

        return ActionResult({"EndpointProperties": endpoint_properties.to_dict()})

    def describe_flywheel(self) -> ActionResult:
        flywheel_arn = self._get_param("FlywheelArn")
        flywheel_properties = self.comprehend_backend.describe_flywheel(
            flywheel_arn=flywheel_arn,
        )

        return ActionResult({"FlywheelProperties": flywheel_properties.to_dict()})

    def delete_document_classifier(self) -> ActionResult:
        document_classifier_arn = self._get_param("DocumentClassifierArn")
        self.comprehend_backend.delete_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )

        return EmptyResult()

    def delete_endpoint(self) -> ActionResult:
        endpoint_arn = self._get_param("EndpointArn")
        self.comprehend_backend.delete_endpoint(
            endpoint_arn=endpoint_arn,
        )

        return EmptyResult()

    def delete_flywheel(self) -> ActionResult:
        flywheel_arn = self._get_param("FlywheelArn")
        self.comprehend_backend.delete_flywheel(
            flywheel_arn=flywheel_arn,
        )

        return EmptyResult()

    def list_document_classifiers(self) -> ActionResult:
        filter = self._get_param("Filter")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        document_classifier_properties_list, next_token = (
            self.comprehend_backend.list_document_classifiers(
                filter=filter,
                next_token=next_token,
                max_results=max_results,
            )
        )

        return ActionResult(
            {
                "DocumentClassifierPropertiesList": document_classifier_properties_list,
                "NextToken": next_token,
            }
        )

    def list_endpoints(self) -> ActionResult:
        filter = self._get_param("Filter")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        endpoint_properties_list, next_token = self.comprehend_backend.list_endpoints(
            filter=filter,
            next_token=next_token,
            max_results=max_results,
        )

        return ActionResult(
            {
                "EndpointPropertiesList": endpoint_properties_list,
                "NextToken": next_token,
            }
        )

    def list_flywheels(self) -> ActionResult:
        filter = self._get_param("Filter")
        next_token = self._get_param("NextToken")
        max_results = self._get_param("MaxResults")
        flywheel_summary_list, next_token = self.comprehend_backend.list_flywheels(
            filter=filter,
            next_token=next_token,
            max_results=max_results,
        )

        return ActionResult(
            {"FlywheelSummaryList": flywheel_summary_list, "nextToken": next_token}
        )

    def stop_training_document_classifier(self) -> ActionResult:
        document_classifier_arn = self._get_param("DocumentClassifierArn")
        self.comprehend_backend.stop_training_document_classifier(
            document_classifier_arn=document_classifier_arn,
        )

        return EmptyResult()

    def start_flywheel_iteration(self) -> ActionResult:
        flywheel_arn = self._get_param("FlywheelArn")
        client_request_token = self._get_param("ClientRequestToken")
        flywheel_arn, flywheel_iteration_id = (
            self.comprehend_backend.start_flywheel_iteration(
                flywheel_arn=flywheel_arn,
                client_request_token=client_request_token,
            )
        )

        return ActionResult(
            {"FlywheelArn": flywheel_arn, "FlywheelIterationId": flywheel_iteration_id}
        )

    def update_endpoint(self) -> ActionResult:
        endpoint_arn = self._get_param("EndpointArn")
        desired_model_arn = self._get_param("DesiredModelArn")
        desired_inference_units = self._get_param("DesiredInferenceUnits")
        desired_data_access_role_arn = self._get_param("DesiredDataAccessRoleArn")
        flywheel_arn = self._get_param("FlywheelArn")
        desired_model_arn = self.comprehend_backend.update_endpoint(
            endpoint_arn=endpoint_arn,
            desired_model_arn=desired_model_arn,
            desired_inference_units=desired_inference_units,
            desired_data_access_role_arn=desired_data_access_role_arn,
            flywheel_arn=flywheel_arn,
        )

        return ActionResult({"DesiredModelArn": desired_model_arn})

    def _job_to_dict_resp(self, job_properties: dict[str, Any]) -> ActionResult:
        job_type_key = job_properties.pop("job_type")

        if job_properties.get("SubmitTime"):
            job_properties["SubmitTime"] = job_properties["SubmitTime"].isoformat()
        if job_properties.get("EndTime"):
            job_properties["EndTime"] = job_properties["EndTime"].isoformat()

        key_name = f"{job_type_key}JobProperties"
        return ActionResult({key_name: job_properties})

    def _list_jobs_to_dict_resp(
        self, job_list: list[dict[str, Any]], job_type: str
    ) -> ActionResult:
        for job_properties in job_list:
            job_properties.pop("job_type")
            if job_properties.get("SubmitTime"):
                job_properties["SubmitTime"] = job_properties["SubmitTime"].isoformat()
            if job_properties.get("EndTime"):
                job_properties["EndTime"] = job_properties["EndTime"].isoformat()

        key_name = f"{job_type}JobPropertiesList"
        return ActionResult({key_name: job_list, "NextToken": None})

    def start_pii_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_pii_entities_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_pii_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_pii_entities_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_pii_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_pii_entities_detection_job(job_id=params["JobId"])
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_pii_entities_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_pii_entities_detection_jobs(
            filter=job_filter
        )
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "PiiEntitiesDetection")

    def start_key_phrases_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_key_phrases_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_key_phrases_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_key_phrases_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_key_phrases_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_key_phrases_detection_job(job_id=params["JobId"])
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_key_phrases_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_key_phrases_detection_jobs(
            filter=job_filter
        )
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "KeyPhrasesDetection")

    def start_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_sentiment_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_sentiment_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_sentiment_detection_job(job_id=params["JobId"])
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_sentiment_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_sentiment_detection_jobs(filter=job_filter)
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "SentimentDetection")

    def put_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        resource_policy = self._get_param("ResourcePolicy")
        policy_revision_id = self._get_param("PolicyRevisionId")

        revision_id = self.comprehend_backend.put_resource_policy(
            resource_arn=resource_arn,
            resource_policy=resource_policy,
            policy_revision_id=policy_revision_id,
        )

        return ActionResult({"PolicyRevisionId": revision_id})

    def describe_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")

        policy_details = self.comprehend_backend.describe_resource_policy(
            resource_arn=resource_arn
        )

        response_payload = {
            "ResourcePolicy": policy_details["ResourcePolicy"],
            "CreationTime": policy_details["CreationTime"].isoformat(),
            "LastModifiedTime": policy_details["LastModifiedTime"].isoformat(),
            "PolicyRevisionId": policy_details["PolicyRevisionId"],
        }

        return ActionResult(response_payload)

    def delete_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy_revision_id = self._get_param("PolicyRevisionId")

        self.comprehend_backend.delete_resource_policy(
            resource_arn=resource_arn,
            policy_revision_id=policy_revision_id,
        )

        return EmptyResult()

    def start_targeted_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_targeted_sentiment_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_targeted_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_targeted_sentiment_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_targeted_sentiment_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_targeted_sentiment_detection_job(
            job_id=params["JobId"]
        )
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_targeted_sentiment_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_targeted_sentiment_detection_jobs(
            filter=job_filter
        )
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "TargetedSentimentDetection")

    def start_dominant_language_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_dominant_language_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_dominant_language_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_dominant_language_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_dominant_language_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_dominant_language_detection_job(
            job_id=params["JobId"]
        )
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_dominant_language_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_dominant_language_detection_jobs(
            filter=job_filter
        )
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "DominantLanguageDetection")

    def start_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_entities_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_entities_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_entities_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_entities_detection_job(job_id=params["JobId"])
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_entities_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_entities_detection_jobs(filter=job_filter)
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "EntitiesDetection")

    def start_topics_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_topics_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_topics_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_topics_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def list_topics_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_topics_detection_jobs(filter=job_filter)
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "TopicsDetection")

    def start_document_classification_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_document_classification_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_document_classification_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_document_classification_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def list_document_classification_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_document_classification_jobs(
            filter=job_filter
        )
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "DocumentClassification")

    def start_events_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.start_events_detection_job(**params)
        return ActionResult(
            {"JobId": job.job_id, "JobArn": job.job_arn, "JobStatus": job.job_status}
        )

    def describe_events_detection_job(self) -> ActionResult:
        params = self._get_params()
        job = self.comprehend_backend.describe_events_detection_job(
            job_id=params["JobId"]
        )
        return self._job_to_dict_resp(job.to_dict())

    def stop_events_detection_job(self) -> ActionResult:
        params = self._get_params()
        self.comprehend_backend.stop_events_detection_job(job_id=params["JobId"])
        return ActionResult({"JobId": params["JobId"], "JobStatus": "STOP_REQUESTED"})

    def list_events_detection_jobs(self) -> ActionResult:
        job_filter = self._get_param("Filter")
        jobs = self.comprehend_backend.list_events_detection_jobs(filter=job_filter)
        job_list = [job.to_dict() for job in jobs]
        return self._list_jobs_to_dict_resp(job_list, "EventsDetection")
