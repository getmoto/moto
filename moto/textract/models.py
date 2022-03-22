"""TextractBackend class with methods for supported APIs."""

import uuid
from random import randint
from collections import defaultdict

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict

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
    PAGES = {"Pages": randint(5, 500)}
    BLOCKS = []

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.async_text_detection_jobs = defaultdict()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.async_text_detection_jobs = defaultdict()
        self.__dict__ = {}
        self.__init__(region_name)

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
        job_id = str(uuid.uuid4())
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
