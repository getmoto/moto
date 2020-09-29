import uuid
from datetime import datetime, timedelta

from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends
from moto.sts.models import ACCOUNT_ID
from .exceptions import ConflictException, BadRequestException


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for i, word in enumerate(key.split("_")):
            words.append(word.title())
        return "".join(words)

    def gen_response_object(self):
        response_object = dict()
        for key, value in self.__dict__.items():
            if "_" in key:
                response_object[self.camelCase(key)] = value
            else:
                response_object[key[0].upper() + key[1:]] = value
        return response_object

    @property
    def response_object(self):
        return self.gen_response_object()


class FakeMedicalTranscriptionJob(BaseObject):
    def __init__(
        self,
        region_name,
        medical_transcription_job_name,
        language_code,
        media_sample_rate_hertz,
        media_format,
        media,
        output_bucket_name,
        output_encryption_kms_key_id,
        settings,
        specialty,
        type,
    ):
        self._region_name = region_name
        self.medical_transcription_job_name = medical_transcription_job_name
        self.transcription_job_status = None
        self.language_code = language_code
        self.media_sample_rate_hertz = media_sample_rate_hertz
        self.media_format = media_format
        self.media = media
        self.transcript = None
        self.start_time = self.completion_time = None
        self.creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.failure_reason = None
        self.settings = settings or {
            "ChannelIdentification": False,
            "ShowAlternatives": False,
        }
        self.specialty = specialty
        self.type = type
        self._output_bucket_name = output_bucket_name
        self._output_encryption_kms_key_id = output_encryption_kms_key_id
        self.output_location_type = "CUSTOMER_BUCKET"

    def response_object(self, response_type):
        response_field_dict = {
            "CREATE": [
                "MedicalTranscriptionJobName",
                "TranscriptionJobStatus",
                "LanguageCode",
                "MediaFormat",
                "Media",
                "StartTime",
                "CreationTime",
                "Specialty",
                "Type",
            ],
            "GET": [
                "MedicalTranscriptionJobName",
                "TranscriptionJobStatus",
                "LanguageCode",
                "MediaSampleRateHertz",
                "MediaFormat",
                "Media",
                "Transcript",
                "StartTime",
                "CreationTime",
                "CompletionTime",
                "Settings",
                "Specialty",
                "Type",
            ],
            "LIST": [
                "MedicalTranscriptionJobName",
                "CreationTime",
                "StartTime",
                "CompletionTime",
                "LanguageCode",
                "TranscriptionJobStatus",
                "FailureReason",
                "OutputLocationType",
                "Specialty",
                "Type",
            ],
        }
        response_fields = response_field_dict[response_type]
        response_object = self.gen_response_object()
        if response_type != "LIST":
            return {
                "MedicalTranscriptionJob": {
                    k: v
                    for k, v in response_object.items()
                    if k in response_fields and v is not None and v != [None]
                }
            }
        else:
            return {
                k: v
                for k, v in response_object.items()
                if k in response_fields and v is not None and v != [None]
            }

    def advance_job_status(self):
        # On each call advances the fake job status

        if not self.transcription_job_status:
            self.transcription_job_status = "QUEUED"
        elif self.transcription_job_status == "QUEUED":
            self.transcription_job_status = "IN_PROGRESS"
            self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not self.media_sample_rate_hertz:
                self.media_sample_rate_hertz = 44100
            if not self.media_format:
                file_ext = self.media["MediaFileUri"].split(".")[-1].lower()
                self.media_format = (
                    file_ext if file_ext in ["mp3", "mp4", "wav", "flac"] else "mp3"
                )
        elif self.transcription_job_status == "IN_PROGRESS":
            self.transcription_job_status = "COMPLETED"
            self.completion_time = (datetime.now() + timedelta(seconds=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.transcript = {
                "TranscriptFileUri": "https://s3.{}.amazonaws.com/{}/medical/{}.json".format(
                    self._region_name,
                    self._output_bucket_name,
                    self.medical_transcription_job_name,
                )
            }


class FakeMedicalVocabulary(BaseObject):
    def __init__(
        self, region_name, vocabulary_name, language_code, vocabulary_file_uri,
    ):
        self._region_name = region_name
        self.vocabulary_name = vocabulary_name
        self.language_code = language_code
        self.vocabulary_file_uri = vocabulary_file_uri
        self.vocabulary_state = None
        self.last_modified_time = None
        self.failure_reason = None
        self.download_uri = "https://s3.us-east-1.amazonaws.com/aws-transcribe-dictionary-model-{}-prod/{}/medical/{}/{}/input.txt".format(
            region_name, ACCOUNT_ID, self.vocabulary_name, uuid.uuid4()
        )

    def response_object(self, response_type):
        response_field_dict = {
            "CREATE": [
                "VocabularyName",
                "LanguageCode",
                "VocabularyState",
                "LastModifiedTime",
                "FailureReason",
            ],
            "GET": [
                "VocabularyName",
                "LanguageCode",
                "VocabularyState",
                "LastModifiedTime",
                "FailureReason",
                "DownloadUri",
            ],
            "LIST": [
                "VocabularyName",
                "LanguageCode",
                "LastModifiedTime",
                "VocabularyState",
            ],
        }
        response_fields = response_field_dict[response_type]
        response_object = self.gen_response_object()
        return {
            k: v
            for k, v in response_object.items()
            if k in response_fields and v is not None and v != [None]
        }

    def advance_job_status(self):
        # On each call advances the fake job status

        if not self.vocabulary_state:
            self.vocabulary_state = "PENDING"
            self.last_modified_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif self.vocabulary_state == "PENDING":
            self.vocabulary_state = "READY"
            self.last_modified_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class TranscribeBackend(BaseBackend):
    def __init__(self, region_name=None):
        self.medical_transcriptions = {}
        self.medical_vocabularies = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def start_medical_transcription_job(self, **kwargs):

        name = kwargs.get("medical_transcription_job_name")

        if name in self.medical_transcriptions:
            raise ConflictException(
                message="The requested job name already exists. Use a different job name."
            )

        settings = kwargs.get("settings")
        vocabulary_name = settings.get("VocabularyName") if settings else None
        if vocabulary_name and vocabulary_name not in self.medical_vocabularies:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. Check the vocabulary name and try your request again."
            )

        transcription_job_object = FakeMedicalTranscriptionJob(
            region_name=self.region_name,
            medical_transcription_job_name=name,
            language_code=kwargs.get("language_code"),
            media_sample_rate_hertz=kwargs.get("media_sample_rate_hertz"),
            media_format=kwargs.get("media_format"),
            media=kwargs.get("media"),
            output_bucket_name=kwargs.get("output_bucket_name"),
            output_encryption_kms_key_id=kwargs.get("output_encryption_kms_key_id"),
            settings=settings,
            specialty=kwargs.get("specialty"),
            type=kwargs.get("type"),
        )

        self.medical_transcriptions[name] = transcription_job_object

        return transcription_job_object.response_object("CREATE")

    def get_medical_transcription_job(self, medical_transcription_job_name):
        try:
            job = self.medical_transcriptions[medical_transcription_job_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. Check the job name and try your request again."
            )

    def delete_medical_transcription_job(self, medical_transcription_job_name):
        try:
            del self.medical_transcriptions[medical_transcription_job_name]
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. Check the job name and try your request again.",
            )

    def list_medical_transcription_jobs(
        self, status, job_name_contains, next_token, max_results
    ):
        jobs = list(self.medical_transcriptions.values())

        if status:
            jobs = [job for job in jobs if job.transcription_job_status == status]

        if job_name_contains:
            jobs = [
                job
                for job in jobs
                if job_name_contains in job.medical_transcription_job_name
            ]

        start_offset = int(next_token) if next_token else 0
        end_offset = start_offset + (
            max_results if max_results else 100
        )  # Arbitrarily selected...
        jobs_paginated = jobs[start_offset:end_offset]

        response = {
            "MedicalTranscriptionJobSummaries": [
                job.response_object("LIST") for job in jobs_paginated
            ]
        }
        if end_offset < len(jobs):
            response["NextToken"] = str(end_offset)
        if status:
            response["Status"] = status
        return response

    def create_medical_vocabulary(self, **kwargs):

        vocabulary_name = kwargs.get("vocabulary_name")
        language_code = kwargs.get("language_code")
        vocabulary_file_uri = kwargs.get("vocabulary_file_uri")

        if vocabulary_name in self.medical_vocabularies:
            raise ConflictException(
                message="The requested vocabulary name already exists. Use a different vocabulary name."
            )

        medical_vocabulary_object = FakeMedicalVocabulary(
            region_name=self.region_name,
            vocabulary_name=vocabulary_name,
            language_code=language_code,
            vocabulary_file_uri=vocabulary_file_uri,
        )

        self.medical_vocabularies[vocabulary_name] = medical_vocabulary_object

        return medical_vocabulary_object.response_object("CREATE")

    def get_medical_vocabulary(self, vocabulary_name):
        try:
            job = self.medical_vocabularies[vocabulary_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. Check the vocabulary name and try your request again."
            )

    def delete_medical_vocabulary(self, vocabulary_name):
        try:
            del self.medical_vocabularies[vocabulary_name]
        except KeyError:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. Check the vocabulary name and try your request again."
            )

    def list_medical_vocabularies(
        self, state_equals, name_contains, next_token, max_results
    ):
        vocabularies = list(self.medical_vocabularies.values())

        if state_equals:
            vocabularies = [
                vocabulary
                for vocabulary in vocabularies
                if vocabulary.vocabulary_state == state_equals
            ]

        if name_contains:
            vocabularies = [
                vocabulary
                for vocabulary in vocabularies
                if name_contains in vocabulary.vocabulary_name
            ]

        start_offset = int(next_token) if next_token else 0
        end_offset = start_offset + (
            max_results if max_results else 100
        )  # Arbitrarily selected...
        vocabularies_paginated = vocabularies[start_offset:end_offset]

        response = {
            "Vocabularies": [
                vocabulary.response_object("LIST")
                for vocabulary in vocabularies_paginated
            ]
        }
        if end_offset < len(vocabularies):
            response["NextToken"] = str(end_offset)
        if state_equals:
            response["Status"] = state_equals
        return response


transcribe_backends = {}
for region, ec2_backend in ec2_backends.items():
    transcribe_backends[region] = TranscribeBackend(region_name=region)
