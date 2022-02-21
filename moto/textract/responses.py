"""Handles incoming textract requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import textract_backends


class TextractResponse(BaseResponse):
    """Handler for Textract requests and responses."""

    @property
    def textract_backend(self):
        """Return backend instance specific for this region."""
        return textract_backends[self.region]

    def get_document_text_detection(self):
        params = json.loads(self.body)
        job_id = params.get("JobId")
        max_results = params.get("MaxResults")
        next_token = params.get("NextToken")
        job = self.textract_backend.get_document_text_detection(
            job_id=job_id, max_results=max_results, next_token=next_token,
        ).to_dict()
        return json.dumps(job)

    def start_document_text_detection(self):
        params = json.loads(self.body)
        document_location = params.get("DocumentLocation")
        client_request_token = params.get("ClientRequestToken")
        job_tag = params.get("JobTag")
        notification_channel = params.get("NotificationChannel")
        output_config = params.get("OutputConfig")
        kms_key_id = params.get("KMSKeyId")
        job_id = self.textract_backend.start_document_text_detection(
            document_location=document_location,
            client_request_token=client_request_token,
            job_tag=job_tag,
            notification_channel=notification_channel,
            output_config=output_config,
            kms_key_id=kms_key_id,
        )
        return json.dumps(dict(JobId=job_id))
