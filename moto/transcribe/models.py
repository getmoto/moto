from datetime import datetime, timedelta

from moto.core import BaseBackend, BaseModel
from moto.core.exceptions import RESTError
from moto.ec2 import ec2_backends


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
        return {
            "MedicalTranscriptionJob": {
                k: v
                for k, v in response_object.items()
                if k in response_fields and v is not None and v != [None]
            }
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


class TranscribeBackend(BaseBackend):
    def __init__(self, region_name=None):
        self.transcriptions = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def start_medical_transcription_job(self, **kwargs):

        name = kwargs.get("medical_transcription_job_name")

        if name in self.transcriptions:
            raise RESTError(
                error_type="ConflictException",
                message="The requested job name already exists. Use a different job name.",
                template="error_json",
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
            settings=kwargs.get("settings"),
            specialty=kwargs.get("specialty"),
            type=kwargs.get("type"),
        )

        self.transcriptions[name] = transcription_job_object

        return transcription_job_object.response_object("CREATE")

    def get_medical_transcription_job(self, medical_transcription_job_name):
        try:
            job = self.transcriptions[medical_transcription_job_name]
            job.advance_job_status()  # Fakes advancement through statuses.
            return job.response_object("GET")
        except KeyError:
            raise RESTError(
                error_type="BadRequestException",
                message="The requested job couldn't be found. Check the job name and try your request again.",
                template="error_json",
            )

    def delete_medical_transcription_job(self, medical_transcription_job_name):
        try:
            del self.transcriptions[medical_transcription_job_name]
        except KeyError:
            raise RESTError(
                error_type="BadRequestException",
                message="The requested job couldn't be found. Check the job name and try your request again.",
                template="error_json",
            )


transcribe_backends = {}
for region, ec2_backend in ec2_backends.items():
    transcribe_backends[region] = TranscribeBackend(region_name=region)
