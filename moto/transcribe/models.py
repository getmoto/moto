import uuid
from datetime import datetime, timedelta
from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.sts.models import ACCOUNT_ID
from .exceptions import ConflictException, BadRequestException


class BaseObject(BaseModel):
    def camelCase(self, key):
        words = []
        for word in key.split("_"):
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


class FakeTranscriptionJob(BaseObject):
    def __init__(
        self,
        region_name,
        transcription_job_name,
        language_code,
        media_sample_rate_hertz,
        media_format,
        media,
        output_bucket_name,
        output_key,
        output_encryption_kms_key_id,
        settings,
        model_settings,
        job_execution_settings,
        content_redaction,
        identify_language,
        language_options,
    ):
        self._region_name = region_name
        self.transcription_job_name = transcription_job_name
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
            "ShowSpeakerLabels": False,
        }
        self.model_settings = model_settings or {"LanguageModelName": None}
        self.job_execution_settings = job_execution_settings or {
            "AllowDeferredExecution": False,
            "DataAccessRoleArn": None,
        }
        self.content_redaction = content_redaction or {
            "RedactionType": None,
            "RedactionOutput": None,
        }
        self.identify_language = identify_language
        self.language_options = language_options
        self.identified_language_score = (None,)
        self._output_bucket_name = output_bucket_name
        self.output_key = output_key
        self._output_encryption_kms_key_id = output_encryption_kms_key_id
        self.output_location_type = (
            "CUSTOMER_BUCKET" if self._output_bucket_name else "SERVICE_BUCKET"
        )

    def response_object(self, response_type):
        response_field_dict = {
            "CREATE": [
                "TranscriptionJobName",
                "TranscriptionJobStatus",
                "LanguageCode",
                "MediaFormat",
                "Media",
                "Settings",
                "StartTime",
                "CreationTime",
                "IdentifyLanguage",
                "LanguageOptions",
                "JobExecutionSettings",
            ],
            "GET": [
                "TranscriptionJobName",
                "TranscriptionJobStatus",
                "LanguageCode",
                "MediaSampleRateHertz",
                "MediaFormat",
                "Media",
                "Settings",
                "Transcript",
                "StartTime",
                "CreationTime",
                "CompletionTime",
                "IdentifyLanguage",
                "LanguageOptions",
                "IdentifiedLanguageScore",
            ],
            "LIST": [
                "TranscriptionJobName",
                "CreationTime",
                "StartTime",
                "CompletionTime",
                "LanguageCode",
                "TranscriptionJobStatus",
                "FailureReason",
                "IdentifyLanguage",
                "IdentifiedLanguageScore",
                "OutputLocationType",
            ],
        }
        response_fields = response_field_dict[response_type]
        response_object = self.gen_response_object()
        if response_type != "LIST":
            return {
                "TranscriptionJob": {
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
            if self.identify_language:
                self.identified_language_score = 0.999645948
                # Simply identify first language passed in lanugage_options
                # If non is set default to "en-US"
                if self.language_options is not None and len(self.language_options) > 0:
                    self.language_code = self.language_options[0]
                else:
                    self.language_code = "en-US"
        elif self.transcription_job_status == "IN_PROGRESS":
            self.transcription_job_status = "COMPLETED"
            self.completion_time = (datetime.now() + timedelta(seconds=10)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if self._output_bucket_name:
                transcript_file_uri = "https://s3.{0}.amazonaws.com/{1}/".format(
                    self._region_name, self._output_bucket_name,
                )
                transcript_file_uri = (
                    transcript_file_uri
                    + "{0}/{1}.json".format(
                        self.output_key, self.transcription_job_name,
                    )
                    if self.output_key is not None
                    else transcript_file_uri
                    + "{transcription_job_name}.json".format(
                        transcription_job_name=self.transcription_job_name
                    )
                )
                self.output_location_type = "CUSTOMER_BUCKET"
            else:
                transcript_file_uri = "https://s3.{0}.amazonaws.com/aws-transcribe-{0}-prod/{1}/{2}/{3}/asrOutput.json".format(  # noqa: E501
                    self._region_name,
                    ACCOUNT_ID,
                    self.transcription_job_name,
                    uuid.uuid4(),
                )
                self.output_location_type = "SERVICE_BUCKET"
            self.transcript = {"TranscriptFileUri": transcript_file_uri}


class FakeVocabulary(BaseObject):
    def __init__(
        self, region_name, vocabulary_name, language_code, phrases, vocabulary_file_uri,
    ):
        self._region_name = region_name
        self.vocabulary_name = vocabulary_name
        self.language_code = language_code
        self.phrases = phrases
        self.vocabulary_file_uri = vocabulary_file_uri
        self.vocabulary_state = None
        self.last_modified_time = None
        self.failure_reason = None
        self.download_uri = "https://s3.{0}.amazonaws.com/aws-transcribe-dictionary-model-{0}-prod/{1}/{2}/{3}/input.txt".format(  # noqa: E501
            region_name, ACCOUNT_ID, vocabulary_name, uuid,
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
        job_type,
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
        self.type = job_type
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
        self.download_uri = "https://s3.us-east-1.amazonaws.com/aws-transcribe-dictionary-model-{}-prod/{}/medical/{}/{}/input.txt".format(  # noqa: E501
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
        self.transcriptions = {}
        self.medical_vocabularies = {}
        self.vocabularies = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint services."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "transcribe"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "transcribestreaming"
        )

    def start_transcription_job(self, **kwargs):

        name = kwargs.get("transcription_job_name")
        if name in self.transcriptions:
            raise ConflictException(
                message="The requested job name already exists. Use a different job name."
            )

        settings = kwargs.get("settings")
        vocabulary_name = settings.get("VocabularyName") if settings else None
        if vocabulary_name and vocabulary_name not in self.vocabularies:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. "
                "Check the vocabulary name and try your request again."
            )

        transcription_job_object = FakeTranscriptionJob(
            region_name=self.region_name,
            transcription_job_name=name,
            language_code=kwargs.get("language_code"),
            media_sample_rate_hertz=kwargs.get("media_sample_rate_hertz"),
            media_format=kwargs.get("media_format"),
            media=kwargs.get("media"),
            output_bucket_name=kwargs.get("output_bucket_name"),
            output_key=kwargs.get("output_key"),
            output_encryption_kms_key_id=kwargs.get("output_encryption_kms_key_id"),
            settings=settings,
            model_settings=kwargs.get("model_settings"),
            job_execution_settings=kwargs.get("job_execution_settings"),
            content_redaction=kwargs.get("content_redaction"),
            identify_language=kwargs.get("identify_language"),
            language_options=kwargs.get("language_options"),
        )
        self.transcriptions[name] = transcription_job_object

        return transcription_job_object.response_object("CREATE")

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
                message="The requested vocabulary couldn't be found. "
                "Check the vocabulary name and try your request again."
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
            job_type=kwargs.get("type"),
        )

        self.medical_transcriptions[name] = transcription_job_object

        return transcription_job_object.response_object("CREATE")

    def get_transcription_job(self, transcription_job_name):
        try:
            job = self.transcriptions[transcription_job_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. "
                "Check the job name and try your request again."
            )

    def get_medical_transcription_job(self, medical_transcription_job_name):
        try:
            job = self.medical_transcriptions[medical_transcription_job_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. "
                "Check the job name and try your request again."
            )

    def delete_transcription_job(self, transcription_job_name):
        try:
            del self.transcriptions[transcription_job_name]
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. "
                "Check the job name and try your request again.",
            )

    def delete_medical_transcription_job(self, medical_transcription_job_name):
        try:
            del self.medical_transcriptions[medical_transcription_job_name]
        except KeyError:
            raise BadRequestException(
                message="The requested job couldn't be found. "
                "Check the job name and try your request again.",
            )

    def list_transcription_jobs(
        self, state_equals, job_name_contains, next_token, max_results
    ):
        jobs = list(self.transcriptions.values())

        if state_equals:
            jobs = [job for job in jobs if job.transcription_job_status == state_equals]

        if job_name_contains:
            jobs = [
                job for job in jobs if job_name_contains in job.transcription_job_name
            ]

        start_offset = int(next_token) if next_token else 0
        end_offset = start_offset + (
            max_results if max_results else 100
        )  # Arbitrarily selected...
        jobs_paginated = jobs[start_offset:end_offset]

        response = {
            "TranscriptionJobSummaries": [
                job.response_object("LIST") for job in jobs_paginated
            ]
        }
        if end_offset < len(jobs):
            response["NextToken"] = str(end_offset)
        if state_equals:
            response["Status"] = state_equals
        return response

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

    def create_vocabulary(self, **kwargs):

        vocabulary_name = kwargs.get("vocabulary_name")
        language_code = kwargs.get("language_code")
        phrases = kwargs.get("phrases")
        vocabulary_file_uri = kwargs.get("vocabulary_file_uri")
        if (
            phrases is not None
            and vocabulary_file_uri is not None
            or phrases is None
            and vocabulary_file_uri is None
        ):
            raise BadRequestException(
                message="Either Phrases or VocabularyFileUri field should be provided.",
            )
        if phrases is not None and len(phrases) < 1:
            raise BadRequestException(
                message="1 validation error detected: Value '[]' at 'phrases' failed to "
                "satisfy constraint: Member must have length greater than or "
                "equal to 1",
            )
        if vocabulary_name in self.vocabularies:
            raise ConflictException(
                message="The requested vocabulary name already exists. "
                "Use a different vocabulary name."
            )

        vocabulary_object = FakeVocabulary(
            region_name=self.region_name,
            vocabulary_name=vocabulary_name,
            language_code=language_code,
            phrases=phrases,
            vocabulary_file_uri=vocabulary_file_uri,
        )

        self.vocabularies[vocabulary_name] = vocabulary_object

        return vocabulary_object.response_object("CREATE")

    def create_medical_vocabulary(self, **kwargs):

        vocabulary_name = kwargs.get("vocabulary_name")
        language_code = kwargs.get("language_code")
        vocabulary_file_uri = kwargs.get("vocabulary_file_uri")

        if vocabulary_name in self.medical_vocabularies:
            raise ConflictException(
                message="The requested vocabulary name already exists. "
                "Use a different vocabulary name."
            )

        medical_vocabulary_object = FakeMedicalVocabulary(
            region_name=self.region_name,
            vocabulary_name=vocabulary_name,
            language_code=language_code,
            vocabulary_file_uri=vocabulary_file_uri,
        )

        self.medical_vocabularies[vocabulary_name] = medical_vocabulary_object

        return medical_vocabulary_object.response_object("CREATE")

    def get_vocabulary(self, vocabulary_name):
        try:
            job = self.vocabularies[vocabulary_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. "
                "Check the vocabulary name and try your request again."
            )

    def get_medical_vocabulary(self, vocabulary_name):
        try:
            job = self.medical_vocabularies[vocabulary_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise BadRequestException(
                message="The requested vocabulary couldn't be found. "
                "Check the vocabulary name and try your request again."
            )

    def delete_vocabulary(self, vocabulary_name):
        try:
            del self.vocabularies[vocabulary_name]
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

    def list_vocabularies(self, state_equals, name_contains, next_token, max_results):
        vocabularies = list(self.vocabularies.values())

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


transcribe_backends = BackendDict(TranscribeBackend, "transcribe")
