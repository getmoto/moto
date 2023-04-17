import json

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from .models import rekognition_backends, RekognitionBackend


class RekognitionResponse(BaseResponse):
    """Handler for Rekognition requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="rekognition")

    @property
    def rekognition_backend(self) -> RekognitionBackend:
        return rekognition_backends[self.current_account][self.region]

    def get_face_search(self) -> str:
        (
            job_status,
            status_message,
            video_metadata,
            persons,
            next_token,
            text_model_version,
        ) = self.rekognition_backend.get_face_search()

        return json.dumps(
            dict(
                JobStatus=job_status,
                StatusMessage=status_message,
                VideoMetadata=video_metadata,
                Persons=persons,
                NextToken=next_token,
                TextModelVersion=text_model_version,
            )
        )

    def get_text_detection(self) -> str:
        (
            job_status,
            status_message,
            video_metadata,
            text_detections,
            next_token,
            text_model_version,
        ) = self.rekognition_backend.get_text_detection()

        return json.dumps(
            dict(
                JobStatus=job_status,
                StatusMessage=status_message,
                VideoMetadata=video_metadata,
                TextDetections=text_detections,
                NextToken=next_token,
                TextModelVersion=text_model_version,
            )
        )

    def start_face_search(self) -> TYPE_RESPONSE:
        headers = {"Content-Type": "application/x-amz-json-1.1"}
        job_id = self.rekognition_backend.start_face_search()
        response = ('{"JobId":"' + job_id + '"}').encode()

        return 200, headers, response

    def start_text_detection(self) -> TYPE_RESPONSE:
        headers = {"Content-Type": "application/x-amz-json-1.1"}
        job_id = self.rekognition_backend.start_text_detection()
        response = ('{"JobId":"' + job_id + '"}').encode()

        return 200, headers, response
