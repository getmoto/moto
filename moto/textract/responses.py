"""Handles incoming textract requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse

from .models import TextractBackend, textract_backends


class TextractResponse(BaseResponse):
    """Handler for Textract requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="textract")
        self.automated_parameter_parsing = True

    @property
    def textract_backend(self) -> TextractBackend:
        """Return backend instance specific for this region."""
        return textract_backends[self.current_account][self.region]

    def get_document_text_detection(self) -> ActionResult:
        job_id = self._get_param("JobId")
        job = self.textract_backend.get_document_text_detection(job_id=job_id)
        result = {
            "Blocks": job.job["Blocks"],
            "DetectDocumentTextModelVersion": job.job["DetectDocumentTextModelVersion"],
            "DocumentMetadata": job.job["DocumentMetadata"],
            "JobStatus": job.job["JobStatus"],
        }
        return ActionResult(result)

    def detect_document_text(self) -> ActionResult:
        result = self.textract_backend.detect_document_text()
        return ActionResult(result)

    def start_document_text_detection(self) -> ActionResult:
        document_location = self._get_param("DocumentLocation")
        notification_channel = self._get_param("NotificationChannel")
        job_id = self.textract_backend.start_document_text_detection(
            document_location=document_location,
            notification_channel=notification_channel,
        )
        return ActionResult({"JobId": job_id})

    def start_document_analysis(self) -> ActionResult:
        document_location = self._get_param("DocumentLocation")
        feature_types = self._get_param("FeatureTypes")
        job_id = self.textract_backend.start_document_analysis(
            document_location=document_location, feature_types=feature_types
        )
        return ActionResult({"JobId": job_id})

    def get_document_analysis(self) -> ActionResult:
        job_id = self._get_param("JobId")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        job = self.textract_backend.get_document_analysis(
            job_id=job_id, max_results=max_results, next_token=next_token
        )
        result = {
            "Blocks": job.job["Blocks"],
            "AnalyzeDocumentModelVersion": job.job["AnalyzeDocumentModelVersion"],
            "DocumentMetadata": job.job["DocumentMetadata"],
            "JobStatus": job.job["JobStatus"],
        }
        return ActionResult(result)
