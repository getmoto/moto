# -*- coding: utf-8 -*-
import boto3
import pytest

from moto import mock_transcribe


@mock_transcribe
def test_run_medical_transcription_job_minimal_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "OutputBucketName": "my-output-bucket",
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    resp = client.start_medical_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # CREATED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["MedicalTranscriptionJobName"] == (
        args["MedicalTranscriptionJobName"]
    )
    assert transcription_job["TranscriptionJobStatus"] == "QUEUED"
    assert transcription_job["LanguageCode"] == args["LanguageCode"]
    assert transcription_job["Media"] == args["Media"]
    assert "CreationTime" in transcription_job
    assert "StartTime" not in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["Settings"]["ChannelIdentification"] is False
    assert transcription_job["Settings"]["ShowAlternatives"] is False
    assert transcription_job["Specialty"] == args["Specialty"]
    assert transcription_job["Type"] == args["Type"]

    # IN_PROGRESS
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
    assert transcription_job["MediaFormat"] == "wav"
    assert "StartTime" in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["MediaSampleRateHertz"] == 44100

    # COMPLETED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CompletionTime" in transcription_job
    assert transcription_job["Transcript"] == {
        "TranscriptFileUri": (
            f"https://s3.{region_name}.amazonaws.com"
            f"/{args['OutputBucketName']}/medical"
            f"/{args['MedicalTranscriptionJobName']}.json"
        ),
    }

    # Delete
    client.delete_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    with pytest.raises(client.exceptions.BadRequestException):
        client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)


@mock_transcribe
def test_run_medical_transcription_job_all_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyMedicalVocabulary"
    resp = client.create_medical_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    job_name = "MyJob2"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "MediaSampleRateHertz": 48000,
        "MediaFormat": "flac",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat"},
        "OutputBucketName": "my-output-bucket",
        "OutputEncryptionKMSKeyId": (
            "arn:aws:kms:us-east-1:012345678901:key"
            "/37111b5e-8eff-4706-ae3a-d4f9d1d559fc"
        ),
        "Settings": {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 5,
            "ChannelIdentification": True,
            "ShowAlternatives": True,
            "MaxAlternatives": 6,
            "VocabularyName": vocabulary_name,
        },
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    resp = client.start_medical_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # CREATED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["MedicalTranscriptionJobName"] == (
        args["MedicalTranscriptionJobName"]
    )
    assert transcription_job["TranscriptionJobStatus"] == "QUEUED"
    assert transcription_job["LanguageCode"] == args["LanguageCode"]
    assert transcription_job["Media"] == args["Media"]
    assert "CreationTime" in transcription_job
    assert "StartTime" not in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["Settings"]["ShowSpeakerLabels"] == (
        args["Settings"]["ShowSpeakerLabels"]
    )
    assert transcription_job["Settings"]["MaxSpeakerLabels"] == (
        args["Settings"]["MaxSpeakerLabels"]
    )
    assert transcription_job["Settings"]["ChannelIdentification"] == (
        args["Settings"]["ChannelIdentification"]
    )
    assert transcription_job["Settings"]["ShowAlternatives"] == (
        args["Settings"]["ShowAlternatives"]
    )
    assert transcription_job["Settings"]["MaxAlternatives"] == (
        args["Settings"]["MaxAlternatives"]
    )
    assert transcription_job["Settings"]["VocabularyName"] == (
        args["Settings"]["VocabularyName"]
    )

    assert transcription_job["Specialty"] == args["Specialty"]
    assert transcription_job["Type"] == args["Type"]

    # IN_PROGRESS
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
    assert transcription_job["MediaFormat"] == "flac"
    assert "StartTime" in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["MediaSampleRateHertz"] == 48000

    # COMPLETED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["MedicalTranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CompletionTime" in transcription_job
    assert transcription_job["Transcript"] == {
        "TranscriptFileUri": (
            f"https://s3.{region_name}.amazonaws.com"
            f"/{args['OutputBucketName']}/medical"
            f"/{args['MedicalTranscriptionJobName']}.json"
        ),
    }


@mock_transcribe
def test_run_transcription_job_all_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    resp = client.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    job_name = "MyJob2"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "MediaSampleRateHertz": 48000,
        "MediaFormat": "flac",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat"},
        "OutputBucketName": "my-output-bucket",
        "OutputEncryptionKMSKeyId": (
            "arn:aws:kms:us-east-1:012345678901:key"
            "/37111b5e-8eff-4706-ae3a-d4f9d1d559fc"
        ),
        "Settings": {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 5,
            "ChannelIdentification": False,
            "ShowAlternatives": True,
            "MaxAlternatives": 6,
            "VocabularyName": vocabulary_name,
        },
        "Subtitles": {
            "Formats": ["srt", "vtt"],
            "OutputStartIndex": 1,
        },
        # Missing `ContentRedaction`, `JobExecutionSettings`,
        # `VocabularyFilterName`, `LanguageModel`
    }
    resp = client.start_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobName"] == args["TranscriptionJobName"]
    assert transcription_job["TranscriptionJobStatus"] == "QUEUED"
    assert transcription_job["LanguageCode"] == args["LanguageCode"]
    assert transcription_job["Media"] == args["Media"]
    assert "CreationTime" in transcription_job
    assert "StartTime" not in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["Settings"]["ShowSpeakerLabels"] == (
        args["Settings"]["ShowSpeakerLabels"]
    )
    assert transcription_job["Settings"]["MaxSpeakerLabels"] == (
        args["Settings"]["MaxSpeakerLabels"]
    )
    assert transcription_job["Settings"]["ChannelIdentification"] == (
        args["Settings"]["ChannelIdentification"]
    )
    assert transcription_job["Settings"]["ShowAlternatives"] == (
        args["Settings"]["ShowAlternatives"]
    )
    assert transcription_job["Settings"]["MaxAlternatives"] == (
        args["Settings"]["MaxAlternatives"]
    )
    assert transcription_job["Settings"]["VocabularyName"] == (
        args["Settings"]["VocabularyName"]
    )
    # IN_PROGRESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
    assert transcription_job["MediaFormat"] == "flac"
    assert "StartTime" in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job
    assert transcription_job["MediaSampleRateHertz"] == 48000

    # COMPLETED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CompletionTime" in transcription_job
    assert transcription_job["Transcript"] == {
        "TranscriptFileUri": (
            f"https://s3.{region_name}.amazonaws.com"
            f"/{args['OutputBucketName']}"
            f"/{args['TranscriptionJobName']}.json"
        ),
    }
    assert transcription_job["Subtitles"] == {
        "Formats": args["Subtitles"]["Formats"],
        "OutputStartIndex": 1,
        "SubtitleFileUris": [
            (
                f"https://s3.{region_name}.amazonaws.com"
                f"/{args['OutputBucketName']}"
                f"/{args['TranscriptionJobName']}.{format}"
            )
            for format in args["Subtitles"]["Formats"]
        ],
    }


@mock_transcribe
def test_run_transcription_job_minimal_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
    }
    resp = client.start_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert "Settings" in transcription_job
    assert transcription_job["Settings"]["ChannelIdentification"] is False
    assert transcription_job["Settings"]["ShowAlternatives"] is False

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobName"] == args["TranscriptionJobName"]
    assert transcription_job["TranscriptionJobStatus"] == "QUEUED"
    assert transcription_job["LanguageCode"] == args["LanguageCode"]
    assert transcription_job["Media"] == args["Media"]
    assert "Settings" in transcription_job
    assert transcription_job["Settings"]["ChannelIdentification"] is False
    assert transcription_job["Settings"]["ShowAlternatives"] is False
    assert "CreationTime" in transcription_job
    assert "StartTime" not in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job

    # QUEUED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
    assert "CreationTime" in transcription_job
    assert "StartTime" in transcription_job
    assert "CompletionTime" not in transcription_job
    assert "Transcript" not in transcription_job

    # IN_PROGESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CreationTime" in transcription_job
    assert "StartTime" in transcription_job
    assert "CompletionTime" in transcription_job
    assert "Transcript" in transcription_job
    # Check aws hosted bucket
    assert (
        f"https://s3.{region_name}.amazonaws.com/aws-transcribe-{region_name}-prod/"
    ) in transcription_job["Transcript"]["TranscriptFileUri"]
    assert transcription_job["Subtitles"] == {
        "Formats": [],
        "OutputStartIndex": 0,
        "SubtitleFileUris": [],
    }

    # Delete
    client.delete_transcription_job(TranscriptionJobName=job_name)
    with pytest.raises(client.exceptions.BadRequestException):
        client.get_transcription_job(TranscriptionJobName=job_name)


@mock_transcribe
def test_run_transcription_job_s3output_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "OutputBucketName": "my-output-bucket",
        "OutputKey": "bucket.json.key.json",
        "Subtitles": {"Formats": ["vtt", "srt"]},
    }
    resp = client.start_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobName"] == args["TranscriptionJobName"]
    assert transcription_job["TranscriptionJobStatus"] == "QUEUED"
    # ... already tested in test_run_transcription_job_minimal_awsoutput_params

    # QUEUED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
    # ... already tested in test_run_transcription_job_minimal_awsoutput_params

    # IN_PROGESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CreationTime" in transcription_job
    assert "StartTime" in transcription_job
    assert "CompletionTime" in transcription_job
    assert "Transcript" in transcription_job
    # Check aws hosted bucket
    assert (
        "https://s3.us-east-1.amazonaws.com/my-output-bucket/bucket.json.key.json"
    ) in transcription_job["Transcript"]["TranscriptFileUri"]
    assert transcription_job["Subtitles"] == {
        "Formats": args["Subtitles"]["Formats"],
        "SubtitleFileUris": [
            f"https://s3.us-east-1.amazonaws.com/my-output-bucket/bucket.json.key.{format}"
            for format in args["Subtitles"]["Formats"]
        ],
    }

    # A new job without an "OutputKey"
    job_name = "MyJob2"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "OutputBucketName": "my-output-bucket",
    }
    client.start_transcription_job(**args)
    # Fast forward ...
    client.get_transcription_job(TranscriptionJobName=job_name)
    client.get_transcription_job(TranscriptionJobName=job_name)
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    transcription_job = resp["TranscriptionJob"]
    assert transcription_job["TranscriptionJobStatus"] == "COMPLETED"
    assert "CreationTime" in transcription_job
    assert "StartTime" in transcription_job
    assert "CompletionTime" in transcription_job
    assert "Transcript" in transcription_job
    # Check aws hosted bucket
    assert transcription_job["Transcript"]["TranscriptFileUri"] == (
        "https://s3.us-east-1.amazonaws.com/my-output-bucket/MyJob2.json"
    )


@mock_transcribe
def test_run_transcription_job_identify_languages_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    # IdentifyLanguage
    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "IdentifyLanguage": True,
        "LanguageOptions": ["en-US", "en-GB", "es-ES", "de-DE"],
    }
    resp_data = [
        client.start_transcription_job(**args),  # CREATED
        client.get_transcription_job(TranscriptionJobName=job_name),  # QUEUED
        client.get_transcription_job(TranscriptionJobName=job_name),  # IN_PROGRESS
        client.list_transcription_jobs(),  # IN_PROGRESS
    ]
    for resp in resp_data:
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        if "TranscriptionJob" in resp:
            transcription_job = resp["TranscriptionJob"]
        elif "TranscriptionJobSummaries" in resp:
            transcription_job = resp["TranscriptionJobSummaries"][0]
        assert "IdentifyLanguage" in transcription_job
        assert "LanguageCodes" not in transcription_job
        assert "IdentifyMultipleLanguages" not in transcription_job
        if "TranscriptionJobStatus" in transcription_job and (
            transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
            or transcription_job["TranscriptionJobStatus"] == "COMPLETED"
        ):
            assert transcription_job["LanguageCode"] == "en-US"
            assert transcription_job["IdentifiedLanguageScore"] == 0.999645948

    # IdentifyMultipleLanguages
    job_name = "MyJob2"
    args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "IdentifyMultipleLanguages": True,
        "LanguageOptions": ["en-US", "en-GB", "es-ES", "de-DE"],
    }
    resp_data = [
        client.start_transcription_job(**args),  # CREATED
        client.get_transcription_job(TranscriptionJobName=job_name),  # QUEUED
        client.get_transcription_job(TranscriptionJobName=job_name),  # IN_PROGRESS
        client.list_transcription_jobs(),  # IN_PROGRESS
    ]
    for resp in resp_data:
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        if "TranscriptionJob" in resp:
            transcription_job = resp["TranscriptionJob"]
        elif "TranscriptionJobSummaries" in resp:
            transcription_job = resp["TranscriptionJobSummaries"][1]
        assert "IdentifyMultipleLanguages" in transcription_job
        assert "LanguageCode" not in transcription_job
        assert "IdentifyLanguage" not in transcription_job
        if "TranscriptionJobStatus" in transcription_job and (
            transcription_job["TranscriptionJobStatus"] == "IN_PROGRESS"
            or transcription_job["TranscriptionJobStatus"] == "COMPLETED"
        ):
            assert transcription_job["LanguageCodes"][0]["LanguageCode"] == "en-US"
            assert transcription_job["LanguageCodes"][0]["DurationInSeconds"] == 123.0
            assert transcription_job["LanguageCodes"][1]["LanguageCode"] == "en-GB"
            assert transcription_job["LanguageCodes"][1]["DurationInSeconds"] == 321.0
            assert transcription_job["IdentifiedLanguageScore"] == 0.999645948


@mock_transcribe
def test_get_nonexistent_medical_transcription_job():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    with pytest.raises(client.exceptions.BadRequestException):
        client.get_medical_transcription_job(
            MedicalTranscriptionJobName="NonexistentJobName"
        )


@mock_transcribe
def test_get_nonexistent_transcription_job():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    with pytest.raises(client.exceptions.BadRequestException):
        client.get_transcription_job(TranscriptionJobName="NonexistentJobName")


@mock_transcribe
def test_run_medical_transcription_job_with_existing_job_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
        "OutputBucketName": "my-output-bucket",
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    resp = client.start_medical_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(client.exceptions.ConflictException):
        client.start_medical_transcription_job(**args)


@mock_transcribe
def test_run_transcription_job_with_existing_job_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
    }
    resp = client.start_transcription_job(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(client.exceptions.ConflictException):
        client.start_transcription_job(**args)


@mock_transcribe
def test_run_medical_transcription_job_nonexistent_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob3"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat"},
        "OutputBucketName": "my-output-bucket",
        "Settings": {"VocabularyName": "NonexistentVocabulary"},
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    with pytest.raises(client.exceptions.BadRequestException):
        client.start_medical_transcription_job(**args)


@mock_transcribe
def test_run_transcription_job_nonexistent_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob3"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat"},
        "OutputBucketName": "my-output-bucket",
        "Settings": {"VocabularyName": "NonexistentVocabulary"},
    }
    with pytest.raises(client.exceptions.BadRequestException):
        client.start_transcription_job(**args)


@mock_transcribe
def test_list_medical_transcription_jobs():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def run_job(index, target_status):
        job_name = f"Job_{index}"
        args = {
            "MedicalTranscriptionJobName": job_name,
            "LanguageCode": "en-US",
            "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
            "OutputBucketName": "my-output-bucket",
            "Specialty": "PRIMARYCARE",
            "Type": "CONVERSATION",
        }
        resp = client.start_medical_transcription_job(**args)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # IMPLICITLY PROMOTE JOB STATUS TO QUEUED
        resp = client.get_medical_transcription_job(
            MedicalTranscriptionJobName=job_name
        )

        # IN_PROGRESS
        if target_status in ["IN_PROGRESS", "COMPLETED"]:
            resp = client.get_medical_transcription_job(
                MedicalTranscriptionJobName=job_name
            )

        # COMPLETED
        if target_status == "COMPLETED":
            resp = client.get_medical_transcription_job(
                MedicalTranscriptionJobName=job_name
            )

    # Run 5 pending jobs
    for i in range(5):
        run_job(i, "PENDING")

    # Run 10 job to IN_PROGRESS
    for i in range(5, 15):
        run_job(i, "IN_PROGRESS")

    # Run 15 job to COMPLETED
    for i in range(15, 30):
        run_job(i, "COMPLETED")

    # List all
    response = client.list_medical_transcription_jobs()
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 30
    assert "NextToken" not in response
    assert "Status" not in response

    # List IN_PROGRESS
    response = client.list_medical_transcription_jobs(Status="IN_PROGRESS")
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 10
    assert "NextToken" not in response
    assert "Status" in response
    assert response["Status"] == "IN_PROGRESS"

    # List JobName contains "8"
    response = client.list_medical_transcription_jobs(JobNameContains="8")
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 3
    assert "NextToken" not in response
    assert "Status" not in response

    # Pagination by 11
    response = client.list_medical_transcription_jobs(MaxResults=11)
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 11
    assert "NextToken" in response
    assert "Status" not in response

    response = client.list_medical_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 11
    assert "NextToken" in response

    response = client.list_medical_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    assert "MedicalTranscriptionJobSummaries" in response
    assert len(response["MedicalTranscriptionJobSummaries"]) == 8
    assert "NextToken" not in response


@mock_transcribe
def test_list_transcription_jobs():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def run_job(index, target_status):
        job_name = f"Job_{index}"
        args = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav"},
            "OutputBucketName": "my-output-bucket",
            "IdentifyLanguage": True,
        }
        resp = client.start_transcription_job(**args)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # IMPLICITLY PROMOTE JOB STATUS TO QUEUED
        resp = client.get_transcription_job(TranscriptionJobName=job_name)

        # IN_PROGRESS
        if target_status in ["IN_PROGRESS", "COMPLETED"]:
            resp = client.get_transcription_job(TranscriptionJobName=job_name)

        # COMPLETED
        if target_status == "COMPLETED":
            resp = client.get_transcription_job(TranscriptionJobName=job_name)

    # Run 5 pending jobs
    for i in range(5):
        run_job(i, "PENDING")

    # Run 10 job to IN_PROGRESS
    for i in range(5, 15):
        run_job(i, "IN_PROGRESS")

    # Run 15 job to COMPLETED
    for i in range(15, 30):
        run_job(i, "COMPLETED")

    # List all
    response = client.list_transcription_jobs()
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 30
    assert "NextToken" not in response
    assert "Status" not in response

    # List IN_PROGRESS
    response = client.list_transcription_jobs(Status="IN_PROGRESS")
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 10
    assert "NextToken" not in response
    assert "Status" in response
    assert response["Status"] == "IN_PROGRESS"

    # List JobName contains "8"
    response = client.list_transcription_jobs(JobNameContains="8")
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 3
    assert "NextToken" not in response
    assert "Status" not in response

    # Pagination by 11
    response = client.list_transcription_jobs(MaxResults=11)
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 11
    assert "NextToken" in response
    assert "Status" not in response

    response = client.list_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 11
    assert "NextToken" in response

    response = client.list_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    assert "TranscriptionJobSummaries" in response
    assert len(response["TranscriptionJobSummaries"]) == 8
    assert "NextToken" not in response


@mock_transcribe
def test_create_medical_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    resp = client.create_medical_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # PENDING
    resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyName"] == vocabulary_name
    assert resp["LanguageCode"] == "en-US"
    assert resp["VocabularyState"] == "PENDING"
    assert "LastModifiedTime" in resp
    assert "FailureReason" not in resp
    assert vocabulary_name in resp["DownloadUri"]

    # IN_PROGRESS
    resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyState"] == "READY"

    # Delete
    client.delete_medical_vocabulary(VocabularyName=vocabulary_name)
    with pytest.raises(client.exceptions.BadRequestException):
        client.get_medical_vocabulary(VocabularyName=vocabulary_name)


@mock_transcribe
def test_create_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    resp = client.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # PENDING
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyName"] == vocabulary_name
    assert resp["LanguageCode"] == "en-US"
    assert resp["VocabularyState"] == "PENDING"
    assert "LastModifiedTime" in resp
    assert "FailureReason" not in resp
    assert vocabulary_name in resp["DownloadUri"]

    # IN_PROGRESS
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyState"] == "READY"

    # Delete
    client.delete_vocabulary(VocabularyName=vocabulary_name)
    with pytest.raises(client.exceptions.BadRequestException):
        client.get_vocabulary(VocabularyName=vocabulary_name)

    # Create another vocabulary with Phrases
    client.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        Phrases=["moto", "is", "awesome"],
    )
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyName"] == vocabulary_name
    assert resp["LanguageCode"] == "en-US"
    assert resp["VocabularyState"] == "PENDING"
    assert vocabulary_name in resp["DownloadUri"]
    assert (
        f"https://s3.{region_name}.amazonaws.com/aws-transcribe-dictionary-model-{region_name}-prod"
    ) in resp["DownloadUri"]
    # IN_PROGRESS
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["VocabularyState"] == "READY"


@mock_transcribe
def test_list_vocabularies():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def create_vocab(index, target_status):
        vocabulary_name = f"Vocab_{index}"
        args = {
            "VocabularyName": vocabulary_name,
            "LanguageCode": "en-US",
            "Phrases": ["moto", "is", "awesome"],
        }
        resp = client.create_vocabulary(**args)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Forward to "PENDING"
        resp = client.get_vocabulary(VocabularyName=vocabulary_name)

        # READY
        if target_status == "READY":
            resp = client.get_vocabulary(VocabularyName=vocabulary_name)

    # Run 5 pending jobs
    for i in range(5):
        create_vocab(i, "PENDING")

    # Run 10 job to IN_PROGRESS
    for i in range(5, 15):
        create_vocab(i, "READY")

    # List all
    response = client.list_vocabularies()
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 15
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List PENDING
    response = client.list_vocabularies(StateEquals="PENDING")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 5
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List READY
    response = client.list_vocabularies(StateEquals="READY")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 10
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List VocabularyName contains "8"
    response = client.list_vocabularies(NameContains="8")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 1
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # Pagination by 3
    response = client.list_vocabularies(MaxResults=3)
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 3
    assert "NextToken" in response
    assert "ResponseMetadata" in response

    response = client.list_vocabularies(NextToken=response["NextToken"], MaxResults=3)
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 3
    assert "NextToken" in response
    assert "ResponseMetadata" in response

    response = client.list_vocabularies(NextToken=response["NextToken"], MaxResults=30)
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 9
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    client.delete_vocabulary(VocabularyName="Vocab_5")
    response = client.list_vocabularies()
    assert len(response["Vocabularies"]) == 14


@mock_transcribe
def test_list_medical_vocabularies():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def create_vocab(index, target_status):
        vocabulary_name = f"Vocab_{index}"
        resp = client.create_medical_vocabulary(
            VocabularyName=vocabulary_name,
            LanguageCode="en-US",
            VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
        )
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Forward to "PENDING"
        resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)

        # READY
        if target_status == "READY":
            resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)

    # Run 5 pending jobs
    for i in range(5):
        create_vocab(i, "PENDING")

    # Run 10 job to IN_PROGRESS
    for i in range(5, 15):
        create_vocab(i, "READY")

    # List all
    response = client.list_medical_vocabularies()
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 15
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List PENDING
    response = client.list_medical_vocabularies(StateEquals="PENDING")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 5
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List READY
    response = client.list_medical_vocabularies(StateEquals="READY")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 10
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # List VocabularyName contains "8"
    response = client.list_medical_vocabularies(NameContains="8")
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 1
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    # Pagination by 3
    response = client.list_medical_vocabularies(MaxResults=3)
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 3
    assert "NextToken" in response
    assert "ResponseMetadata" in response

    response = client.list_medical_vocabularies(
        NextToken=response["NextToken"], MaxResults=3
    )
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 3
    assert "NextToken" in response
    assert "ResponseMetadata" in response

    response = client.list_medical_vocabularies(
        NextToken=response["NextToken"], MaxResults=30
    )
    assert "Vocabularies" in response
    assert len(response["Vocabularies"]) == 9
    assert "NextToken" not in response
    assert "ResponseMetadata" in response

    client.delete_medical_vocabulary(VocabularyName="Vocab_5")
    response = client.list_medical_vocabularies()
    assert len(response["Vocabularies"]) == 14


@mock_transcribe
def test_get_nonexistent_medical_vocabulary():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    with pytest.raises(client.exceptions.BadRequestException):
        client.get_medical_vocabulary(VocabularyName="NonexistentVocabularyName")


@mock_transcribe
def test_get_nonexistent_vocabulary():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    with pytest.raises(client.exceptions.BadRequestException):
        client.get_vocabulary(VocabularyName="NonexistentVocabularyName")


@mock_transcribe
def test_create_medical_vocabulary_with_existing_vocabulary_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    args = {
        "VocabularyName": vocabulary_name,
        "LanguageCode": "en-US",
        "VocabularyFileUri": "https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    }
    resp = client.create_medical_vocabulary(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(client.exceptions.ConflictException):
        client.create_medical_vocabulary(**args)


@mock_transcribe
def test_create_vocabulary_with_existing_vocabulary_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    args = {
        "VocabularyName": vocabulary_name,
        "LanguageCode": "en-US",
        "VocabularyFileUri": "https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
    }
    resp = client.create_vocabulary(**args)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    with pytest.raises(client.exceptions.ConflictException):
        client.create_vocabulary(**args)


@mock_transcribe
def test_create_vocabulary_with_bad_request():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    args = {
        "VocabularyName": vocabulary_name,
        "LanguageCode": "en-US",
    }
    with pytest.raises(client.exceptions.BadRequestException):
        client.create_vocabulary(**args)

    args = {
        "VocabularyName": vocabulary_name,
        "Phrases": [],
        "LanguageCode": "en-US",
    }
    with pytest.raises(client.exceptions.BadRequestException):
        client.create_vocabulary(**args)
