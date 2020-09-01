from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .models import transcribe_backends


class TranscribeResponse(BaseResponse):
    @property
    def transcribe_backend(self):
        return transcribe_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    @amzn_request_id
    def start_medical_transcription_job(self):
        name = self._get_param("MedicalTranscriptionJobName")
        response = self.transcribe_backend.start_medical_transcription_job(
            medical_transcription_job_name=name,
            language_code=self._get_param("LanguageCode"),
            media_sample_rate_hertz=self._get_param("MediaSampleRateHertz"),
            media_format=self._get_param("MediaFormat"),
            media=self._get_param("Media"),
            output_bucket_name=self._get_param("OutputBucketName"),
            output_encryption_kms_key_id=self._get_param("OutputEncryptionKMSKeyId"),
            settings=self._get_param("Settings"),
            specialty=self._get_param("Specialty"),
            type=self._get_param("Type"),
        )
        return json.dumps(response)

    @amzn_request_id
    def get_medical_transcription_job(self):
        medical_transcription_job_name = self._get_param("MedicalTranscriptionJobName")
        response = self.transcribe_backend.get_medical_transcription_job(
            medical_transcription_job_name=medical_transcription_job_name
        )
        return json.dumps(response)

    @amzn_request_id
    def delete_medical_transcription_job(self):
        medical_transcription_job_name = self._get_param("MedicalTranscriptionJobName")
        response = self.transcribe_backend.delete_medical_transcription_job(
            medical_transcription_job_name=medical_transcription_job_name
        )
        return json.dumps(response)
