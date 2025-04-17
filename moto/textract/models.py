import json
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.sns import sns_backends

from .exceptions import InvalidJobIdException, InvalidParameterException


class TextractJobStatus:
    in_progress = "IN_PROGRESS"
    succeeded = "SUCCEEDED"
    failed = "FAILED"
    partial_success = "PARTIAL_SUCCESS"


class TextractJob(BaseModel):
    def __init__(
        self, job: Dict[str, Any], notification_channel: Optional[Dict[str, str]] = None
    ):
        self.job = job
        self.notification_channel = notification_channel
        self.job_id = str(mock_random.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return self.job

    def send_completion_notification(
        self, account_id: str, region_name: str, document_location: Dict[str, Any]
    ) -> None:
        if not self.notification_channel:
            return

        topic_arn = self.notification_channel.get("SNSTopicArn")
        if not topic_arn:
            return

        # Convert document_location from {'S3Object': {'Bucket': '...', 'Name': '...'}} format
        # to {'S3Bucket': '...', 'S3ObjectName': '...'} format as per AWS docs
        s3_object = document_location.get("S3Object", {})
        doc_location = {
            "S3Bucket": s3_object.get("Bucket", ""),
            "S3ObjectName": s3_object.get("Name", ""),
        }

        notification = {
            "JobId": self.job_id,
            "Status": self.job["JobStatus"],
            "API": "StartDocumentTextDetection",
            "JobTag": "",  # Not implemented yet
            "Timestamp": int(time.time() * 1000),  # Convert to milliseconds
            "DocumentLocation": doc_location,
        }

        sns_backend = sns_backends[account_id][region_name]
        sns_backend.publish(
            message=json.dumps(notification),  # SNS requires message to be a string
            arn=topic_arn,
            subject="Amazon Textract Job Completion",
        )


class TextractBackend(BaseBackend):
    """Implementation of Textract APIs."""

    JOB_STATUS = TextractJobStatus.succeeded
    PAGES = {"Pages": mock_random.randint(5, 500)}
    BLOCKS: List[Dict[str, Any]] = []

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.async_text_detection_jobs: Dict[str, TextractJob] = defaultdict()

    def get_document_text_detection(self, job_id: str) -> TextractJob:
        """
        Pagination has not yet been implemented
        """
        job = self.async_text_detection_jobs.get(job_id)
        if not job:
            raise InvalidJobIdException()
        return job

    def detect_document_text(self) -> Dict[str, Any]:
        return {
            "Blocks": TextractBackend.BLOCKS,
            "DetectDocumentTextModelVersion": "1.0",
            "DocumentMetadata": {"Pages": TextractBackend.PAGES},
        }

    def start_document_text_detection(
        self,
        document_location: Dict[str, Any],
        notification_channel: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        The following parameters have not yet been implemented: ClientRequestToken, JobTag, OutputConfig, KmsKeyID
        """
        if not document_location:
            raise InvalidParameterException()

        job = TextractJob(
            {
                "Blocks": TextractBackend.BLOCKS,
                "DetectDocumentTextModelVersion": "1.0",
                "DocumentMetadata": {"Pages": TextractBackend.PAGES},
                "JobStatus": TextractBackend.JOB_STATUS,
            },
            notification_channel=notification_channel,
        )

        self.async_text_detection_jobs[job.job_id] = job

        # Send completion notification since we're mocking an immediate completion
        job.send_completion_notification(
            self.account_id, self.region_name, document_location
        )

        return job.job_id


textract_backends = BackendDict(TextractBackend, "textract")
