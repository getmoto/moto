"""Handles incoming textract requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import textract_backends, TextractBackend


class TextractResponse(BaseResponse):
    """Handler for Textract requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="textract")

    @property
    def textract_backend(self) -> TextractBackend:
        """Return backend instance specific for this region."""
        return textract_backends[self.current_account][self.region]

    def get_document_text_detection(self) -> str:
        params = json.loads(self.body)
        job_id = params.get("JobId")
        job = self.textract_backend.get_document_text_detection(job_id=job_id).to_dict()
        return json.dumps(job)

    def start_document_text_detection(self) -> str:
        params = json.loads(self.body)
        document_location = params.get("DocumentLocation")
        job_id = self.textract_backend.start_document_text_detection(
            document_location=document_location
        )
        return json.dumps(dict(JobId=job_id))
