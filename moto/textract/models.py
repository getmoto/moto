"""TextractBackend class with methods for supported APIs."""

from collections import defaultdict

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.moto_api._internal import mock_random

from .exceptions import InvalidParameterException, InvalidJobIdException


class TextractJobStatus:
    in_progress = "IN_PROGRESS"
    succeeded = "SUCCEEDED"
    failed = "FAILED"
    partial_success = "PARTIAL_SUCCESS"


class TextractJob(BaseModel):
    def __init__(self, job):
        self.job = job

    def to_dict(self):
        return self.job


class TextractBackend(BaseBackend):
    """Implementation of Textract APIs."""

    JOB_STATUS = TextractJobStatus.succeeded
    PAGES = {"Pages": mock_random.randint(5, 500)}
    BLOCKS = []

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.async_text_detection_jobs = defaultdict()

    def get_document_text_detection(self, job_id):
        """
        Pagination has not yet been implemented
        """
        job = self.async_text_detection_jobs.get(job_id)
        if not job:
            raise InvalidJobIdException()
        return job

    def start_document_text_detection(self, document_location):
        """
        The following parameters have not yet been implemented: ClientRequestToken, JobTag, NotificationChannel, OutputConfig, KmsKeyID
        """
        if not document_location:
            raise InvalidParameterException()
        job_id = str(mock_random.uuid4())
        self.async_text_detection_jobs[job_id] = TextractJob(
            {
                "Blocks": TextractBackend.BLOCKS,
                "DetectDocumentTextModelVersion": "1.0",
                "DocumentMetadata": {"Pages": TextractBackend.PAGES},
                "JobStatus": TextractBackend.JOB_STATUS,
            }
        )
        return job_id


textract_backends = BackendDict(TextractBackend, "textract")
