# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_transcribe


@mock_transcribe
def test_run_medical_transcription_job_minimal_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
        "OutputBucketName": "my-output-bucket",
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    resp = client.start_medical_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # CREATED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["MedicalTranscriptionJobName"].should.equal(
        args["MedicalTranscriptionJobName"]
    )
    transcription_job["TranscriptionJobStatus"].should.equal("QUEUED")
    transcription_job["LanguageCode"].should.equal(args["LanguageCode"])
    transcription_job["Media"].should.equal(args["Media"])
    transcription_job.should.contain("CreationTime")
    transcription_job.doesnt.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["Settings"]["ChannelIdentification"].should.equal(False)
    transcription_job["Settings"]["ShowAlternatives"].should.equal(False)
    transcription_job["Specialty"].should.equal(args["Specialty"])
    transcription_job["Type"].should.equal(args["Type"])

    # IN_PROGRESS
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("IN_PROGRESS")
    transcription_job["MediaFormat"].should.equal("wav")
    transcription_job.should.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["MediaSampleRateHertz"].should.equal(44100)

    # COMPLETED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CompletionTime")
    transcription_job["Transcript"].should.equal(
        {
            "TranscriptFileUri": "https://s3.{}.amazonaws.com/{}/medical/{}.json".format(
                region_name,
                args["OutputBucketName"],
                args["MedicalTranscriptionJobName"],
            )
        }
    )

    # Delete
    client.delete_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    client.get_medical_transcription_job.when.called_with(
        MedicalTranscriptionJobName=job_name
    ).should.throw(client.exceptions.BadRequestException)


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    job_name = "MyJob2"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "MediaSampleRateHertz": 48000,
        "MediaFormat": "flac",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat",},
        "OutputBucketName": "my-output-bucket",
        "OutputEncryptionKMSKeyId": "arn:aws:kms:us-east-1:012345678901:key/37111b5e-8eff-4706-ae3a-d4f9d1d559fc",
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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # CREATED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["MedicalTranscriptionJobName"].should.equal(
        args["MedicalTranscriptionJobName"]
    )
    transcription_job["TranscriptionJobStatus"].should.equal("QUEUED")
    transcription_job["LanguageCode"].should.equal(args["LanguageCode"])
    transcription_job["Media"].should.equal(args["Media"])
    transcription_job.should.contain("CreationTime")
    transcription_job.doesnt.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["Settings"]["ShowSpeakerLabels"].should.equal(
        args["Settings"]["ShowSpeakerLabels"]
    )
    transcription_job["Settings"]["MaxSpeakerLabels"].should.equal(
        args["Settings"]["MaxSpeakerLabels"]
    )
    transcription_job["Settings"]["ChannelIdentification"].should.equal(
        args["Settings"]["ChannelIdentification"]
    )
    transcription_job["Settings"]["ShowAlternatives"].should.equal(
        args["Settings"]["ShowAlternatives"]
    )
    transcription_job["Settings"]["MaxAlternatives"].should.equal(
        args["Settings"]["MaxAlternatives"]
    )
    transcription_job["Settings"]["VocabularyName"].should.equal(
        args["Settings"]["VocabularyName"]
    )

    transcription_job["Specialty"].should.equal(args["Specialty"])
    transcription_job["Type"].should.equal(args["Type"])

    # IN_PROGRESS
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("IN_PROGRESS")
    transcription_job["MediaFormat"].should.equal("flac")
    transcription_job.should.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["MediaSampleRateHertz"].should.equal(48000)

    # COMPLETED
    resp = client.get_medical_transcription_job(MedicalTranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["MedicalTranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CompletionTime")
    transcription_job["Transcript"].should.equal(
        {
            "TranscriptFileUri": "https://s3.{}.amazonaws.com/{}/medical/{}.json".format(
                region_name,
                args["OutputBucketName"],
                args["MedicalTranscriptionJobName"],
            )
        }
    )


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    job_name = "MyJob2"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "MediaSampleRateHertz": 48000,
        "MediaFormat": "flac",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat",},
        "OutputBucketName": "my-output-bucket",
        "OutputEncryptionKMSKeyId": "arn:aws:kms:us-east-1:012345678901:key/37111b5e-8eff-4706-ae3a-d4f9d1d559fc",
        "Settings": {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 5,
            "ChannelIdentification": False,
            "ShowAlternatives": True,
            "MaxAlternatives": 6,
            "VocabularyName": vocabulary_name,
        },
        # Missing `ContentRedaction`, `JobExecutionSettings`, `VocabularyFilterName`, `LanguageModel`
    }
    resp = client.start_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobName"].should.equal(args["TranscriptionJobName"])
    transcription_job["TranscriptionJobStatus"].should.equal("QUEUED")
    transcription_job["LanguageCode"].should.equal(args["LanguageCode"])
    transcription_job["Media"].should.equal(args["Media"])
    transcription_job.should.contain("CreationTime")
    transcription_job.doesnt.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["Settings"]["ShowSpeakerLabels"].should.equal(
        args["Settings"]["ShowSpeakerLabels"]
    )
    transcription_job["Settings"]["MaxSpeakerLabels"].should.equal(
        args["Settings"]["MaxSpeakerLabels"]
    )
    transcription_job["Settings"]["ChannelIdentification"].should.equal(
        args["Settings"]["ChannelIdentification"]
    )
    transcription_job["Settings"]["ShowAlternatives"].should.equal(
        args["Settings"]["ShowAlternatives"]
    )
    transcription_job["Settings"]["MaxAlternatives"].should.equal(
        args["Settings"]["MaxAlternatives"]
    )
    transcription_job["Settings"]["VocabularyName"].should.equal(
        args["Settings"]["VocabularyName"]
    )
    # IN_PROGRESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("IN_PROGRESS")
    transcription_job["MediaFormat"].should.equal("flac")
    transcription_job.should.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")
    transcription_job["MediaSampleRateHertz"].should.equal(48000)

    # COMPLETED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CompletionTime")
    transcription_job["Transcript"].should.equal(
        {
            "TranscriptFileUri": "https://s3.{}.amazonaws.com/{}/{}.json".format(
                region_name, args["OutputBucketName"], args["TranscriptionJobName"],
            )
        }
    )


@mock_transcribe
def test_run_transcription_job_minimal_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
    }
    resp = client.start_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job.should.contain("Settings")
    transcription_job["Settings"]["ChannelIdentification"].should.equal(False)
    transcription_job["Settings"]["ShowAlternatives"].should.equal(False)

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobName"].should.equal(args["TranscriptionJobName"])
    transcription_job["TranscriptionJobStatus"].should.equal("QUEUED")
    transcription_job["LanguageCode"].should.equal(args["LanguageCode"])
    transcription_job["Media"].should.equal(args["Media"])
    transcription_job.should.contain("Settings")
    transcription_job["Settings"]["ChannelIdentification"].should.equal(False)
    transcription_job["Settings"]["ShowAlternatives"].should.equal(False)
    transcription_job.should.contain("CreationTime")
    transcription_job.doesnt.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")

    # QUEUED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("IN_PROGRESS")
    transcription_job.should.contain("CreationTime")
    transcription_job.should.contain("StartTime")
    transcription_job.doesnt.contain("CompletionTime")
    transcription_job.doesnt.contain("Transcript")

    # IN_PROGESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CreationTime")
    transcription_job.should.contain("StartTime")
    transcription_job.should.contain("CompletionTime")
    transcription_job.should.contain("Transcript")
    # Check aws hosted bucket
    transcription_job["Transcript"]["TranscriptFileUri"].should.contain(
        "https://s3.{0}.amazonaws.com/aws-transcribe-{0}-prod/".format(region_name)
    )

    # Delete
    client.delete_transcription_job(TranscriptionJobName=job_name)
    client.get_transcription_job.when.called_with(
        TranscriptionJobName=job_name
    ).should.throw(client.exceptions.BadRequestException)


@mock_transcribe
def test_run_transcription_job_s3output_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
        "OutputBucketName": "my-output-bucket",
        "OutputKey": "bucket-key",
    }
    resp = client.start_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # CREATED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobName"].should.equal(args["TranscriptionJobName"])
    transcription_job["TranscriptionJobStatus"].should.equal("QUEUED")
    # ... already tested in test_run_transcription_job_minimal_awsoutput_params

    # QUEUED
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("IN_PROGRESS")
    # ... already tested in test_run_transcription_job_minimal_awsoutput_params

    # IN_PROGESS
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CreationTime")
    transcription_job.should.contain("StartTime")
    transcription_job.should.contain("CompletionTime")
    transcription_job.should.contain("Transcript")
    # Check aws hosted bucket
    transcription_job["Transcript"]["TranscriptFileUri"].should.contain(
        "https://s3.us-east-1.amazonaws.com/my-output-bucket/bucket-key/MyJob.json".format(
            region_name
        )
    )
    # A new job without an "OutputKey"
    job_name = "MyJob2"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
        "OutputBucketName": "my-output-bucket",
    }
    client.start_transcription_job(**args)
    # Fast forward ...
    client.get_transcription_job(TranscriptionJobName=job_name)
    client.get_transcription_job(TranscriptionJobName=job_name)
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job["TranscriptionJobStatus"].should.equal("COMPLETED")
    transcription_job.should.contain("CreationTime")
    transcription_job.should.contain("StartTime")
    transcription_job.should.contain("CompletionTime")
    transcription_job.should.contain("Transcript")
    # Check aws hosted bucket
    transcription_job["Transcript"]["TranscriptFileUri"].should.equal(
        "https://s3.us-east-1.amazonaws.com/my-output-bucket/MyJob2.json"
    )


@mock_transcribe
def test_run_transcription_job_identify_language_params():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
        "IdentifyLanguage": True,
        "LanguageOptions": ["en-US", "en-GB", "es-ES", "de-DE"],
    }
    resp = client.start_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    transcription_job = resp["TranscriptionJob"]
    transcription_job.should.contain("IdentifyLanguage")
    transcription_job.should.contain("LanguageOptions")
    client.get_transcription_job(TranscriptionJobName=job_name)
    resp = client.get_transcription_job(TranscriptionJobName=job_name)
    transcription_job = resp["TranscriptionJob"]
    transcription_job.should.contain("LanguageCode")
    transcription_job.should.contain("IdentifiedLanguageScore")
    transcription_job["LanguageCode"].should.equal("en-US")
    transcription_job["IdentifiedLanguageScore"].should.equal(0.999645948)


@mock_transcribe
def test_get_nonexistent_medical_transcription_job():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    client.get_medical_transcription_job.when.called_with(
        MedicalTranscriptionJobName="NonexistentJobName"
    ).should.throw(client.exceptions.BadRequestException)


@mock_transcribe
def test_get_nonexistent_transcription_job():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    client.get_transcription_job.when.called_with(
        TranscriptionJobName="NonexistentJobName"
    ).should.throw(client.exceptions.BadRequestException)


@mock_transcribe
def test_run_medical_transcription_job_with_existing_job_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
        "OutputBucketName": "my-output-bucket",
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    resp = client.start_medical_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    client.start_medical_transcription_job.when.called_with(**args).should.throw(
        client.exceptions.ConflictException
    )


@mock_transcribe
def test_run_transcription_job_with_existing_job_name():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
    }
    resp = client.start_transcription_job(**args)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    client.start_transcription_job.when.called_with(**args).should.throw(
        client.exceptions.ConflictException
    )


@mock_transcribe
def test_run_medical_transcription_job_nonexistent_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob3"
    args = {
        "MedicalTranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat",},
        "OutputBucketName": "my-output-bucket",
        "Settings": {"VocabularyName": "NonexistentVocabulary"},
        "Specialty": "PRIMARYCARE",
        "Type": "CONVERSATION",
    }
    client.start_medical_transcription_job.when.called_with(**args).should.throw(
        client.exceptions.BadRequestException
    )


@mock_transcribe
def test_run_transcription_job_nonexistent_vocabulary():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    job_name = "MyJob3"
    args = {
        "TranscriptionJobName": job_name,
        "LanguageCode": "en-US",
        "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.dat",},
        "OutputBucketName": "my-output-bucket",
        "Settings": {"VocabularyName": "NonexistentVocabulary"},
    }
    client.start_transcription_job.when.called_with(**args).should.throw(
        client.exceptions.BadRequestException
    )


@mock_transcribe
def test_list_medical_transcription_jobs():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def run_job(index, target_status):
        job_name = "Job_{}".format(index)
        args = {
            "MedicalTranscriptionJobName": job_name,
            "LanguageCode": "en-US",
            "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
            "OutputBucketName": "my-output-bucket",
            "Specialty": "PRIMARYCARE",
            "Type": "CONVERSATION",
        }
        resp = client.start_medical_transcription_job(**args)
        resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(30)
    response.shouldnt.contain("NextToken")
    response.shouldnt.contain("Status")

    # List IN_PROGRESS
    response = client.list_medical_transcription_jobs(Status="IN_PROGRESS")
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(10)
    response.shouldnt.contain("NextToken")
    response.should.contain("Status")
    response["Status"].should.equal("IN_PROGRESS")

    # List JobName contains "8"
    response = client.list_medical_transcription_jobs(JobNameContains="8")
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(3)
    response.shouldnt.contain("NextToken")
    response.shouldnt.contain("Status")

    # Pagination by 11
    response = client.list_medical_transcription_jobs(MaxResults=11)
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(11)
    response.should.contain("NextToken")
    response.shouldnt.contain("Status")

    response = client.list_medical_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(11)
    response.should.contain("NextToken")

    response = client.list_medical_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    response.should.contain("MedicalTranscriptionJobSummaries")
    len(response["MedicalTranscriptionJobSummaries"]).should.equal(8)
    response.shouldnt.contain("NextToken")


@mock_transcribe
def test_list_transcription_jobs():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def run_job(index, target_status):
        job_name = "Job_{}".format(index)
        args = {
            "TranscriptionJobName": job_name,
            "Media": {"MediaFileUri": "s3://my-bucket/my-media-file.wav",},
            "OutputBucketName": "my-output-bucket",
            "IdentifyLanguage": True,
        }
        resp = client.start_transcription_job(**args)
        resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(30)
    response.shouldnt.contain("NextToken")
    response.shouldnt.contain("Status")

    # List IN_PROGRESS
    response = client.list_transcription_jobs(Status="IN_PROGRESS")
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(10)
    response.shouldnt.contain("NextToken")
    response.should.contain("Status")
    response["Status"].should.equal("IN_PROGRESS")

    # List JobName contains "8"
    response = client.list_transcription_jobs(JobNameContains="8")
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(3)
    response.shouldnt.contain("NextToken")
    response.shouldnt.contain("Status")

    # Pagination by 11
    response = client.list_transcription_jobs(MaxResults=11)
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(11)
    response.should.contain("NextToken")
    response.shouldnt.contain("Status")

    response = client.list_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(11)
    response.should.contain("NextToken")

    response = client.list_transcription_jobs(
        NextToken=response["NextToken"], MaxResults=11
    )
    response.should.contain("TranscriptionJobSummaries")
    len(response["TranscriptionJobSummaries"]).should.equal(8)
    response.shouldnt.contain("NextToken")


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # PENDING
    resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyName"].should.equal(vocabulary_name)
    resp["LanguageCode"].should.equal("en-US")
    resp["VocabularyState"].should.equal("PENDING")
    resp.should.contain("LastModifiedTime")
    resp.shouldnt.contain("FailureReason")
    resp["DownloadUri"].should.contain(vocabulary_name)

    # IN_PROGRESS
    resp = client.get_medical_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyState"].should.equal("READY")

    # Delete
    client.delete_medical_vocabulary(VocabularyName=vocabulary_name)
    client.get_medical_vocabulary.when.called_with(
        VocabularyName=vocabulary_name
    ).should.throw(client.exceptions.BadRequestException)


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # PENDING
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyName"].should.equal(vocabulary_name)
    resp["LanguageCode"].should.equal("en-US")
    resp["VocabularyState"].should.equal("PENDING")
    resp.should.contain("LastModifiedTime")
    resp.shouldnt.contain("FailureReason")
    resp["DownloadUri"].should.contain(vocabulary_name)

    # IN_PROGRESS
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyState"].should.equal("READY")

    # Delete
    client.delete_vocabulary(VocabularyName=vocabulary_name)
    client.get_vocabulary.when.called_with(VocabularyName=vocabulary_name).should.throw(
        client.exceptions.BadRequestException
    )

    # Create another vocabulary with Phrases
    client.create_vocabulary(
        VocabularyName=vocabulary_name,
        LanguageCode="en-US",
        Phrases=["moto", "is", "awesome"],
    )
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyName"].should.equal(vocabulary_name)
    resp["LanguageCode"].should.equal("en-US")
    resp["VocabularyState"].should.equal("PENDING")
    resp["DownloadUri"].should.contain(vocabulary_name)
    resp["DownloadUri"].should.contain(
        "https://s3.{0}.amazonaws.com/aws-transcribe-dictionary-model-{0}-prod".format(
            region_name
        )
    )
    # IN_PROGRESS
    resp = client.get_vocabulary(VocabularyName=vocabulary_name)
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    resp["VocabularyState"].should.equal("READY")


@mock_transcribe
def test_list_vocabularies():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def create_vocab(index, target_status):
        vocabulary_name = "Vocab_{}".format(index)
        args = {
            "VocabularyName": vocabulary_name,
            "LanguageCode": "en-US",
            "Phrases": ["moto", "is", "awesome"],
        }
        resp = client.create_vocabulary(**args)
        resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(15)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List PENDING
    response = client.list_vocabularies(StateEquals="PENDING")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(5)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List READY
    response = client.list_vocabularies(StateEquals="READY")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(10)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List VocabularyName contains "8"
    response = client.list_vocabularies(NameContains="8")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(1)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # Pagination by 3
    response = client.list_vocabularies(MaxResults=3)
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(3)
    response.should.contain("NextToken")
    response.should.contain("ResponseMetadata")

    response = client.list_vocabularies(NextToken=response["NextToken"], MaxResults=3)
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(3)
    response.should.contain("NextToken")
    response.should.contain("ResponseMetadata")

    response = client.list_vocabularies(NextToken=response["NextToken"], MaxResults=30)
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(9)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    client.delete_vocabulary(VocabularyName="Vocab_5")
    response = client.list_vocabularies()
    len(response["Vocabularies"]).should.equal(14)


@mock_transcribe
def test_list_medical_vocabularies():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    def create_vocab(index, target_status):
        vocabulary_name = "Vocab_{}".format(index)
        resp = client.create_medical_vocabulary(
            VocabularyName=vocabulary_name,
            LanguageCode="en-US",
            VocabularyFileUri="https://s3.us-east-1.amazonaws.com/AWSDOC-EXAMPLE-BUCKET/vocab.txt",
        )
        resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(15)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List PENDING
    response = client.list_medical_vocabularies(StateEquals="PENDING")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(5)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List READY
    response = client.list_medical_vocabularies(StateEquals="READY")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(10)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # List VocabularyName contains "8"
    response = client.list_medical_vocabularies(NameContains="8")
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(1)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    # Pagination by 3
    response = client.list_medical_vocabularies(MaxResults=3)
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(3)
    response.should.contain("NextToken")
    response.should.contain("ResponseMetadata")

    response = client.list_medical_vocabularies(
        NextToken=response["NextToken"], MaxResults=3
    )
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(3)
    response.should.contain("NextToken")
    response.should.contain("ResponseMetadata")

    response = client.list_medical_vocabularies(
        NextToken=response["NextToken"], MaxResults=30
    )
    response.should.contain("Vocabularies")
    len(response["Vocabularies"]).should.equal(9)
    response.shouldnt.contain("NextToken")
    response.should.contain("ResponseMetadata")

    client.delete_medical_vocabulary(VocabularyName="Vocab_5")
    response = client.list_medical_vocabularies()
    len(response["Vocabularies"]).should.equal(14)


@mock_transcribe
def test_get_nonexistent_medical_vocabulary():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    client.get_medical_vocabulary.when.called_with(
        VocabularyName="NonexistentVocabularyName"
    ).should.throw(client.exceptions.BadRequestException)


@mock_transcribe
def test_get_nonexistent_vocabulary():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    client.get_vocabulary.when.called_with(
        VocabularyName="NonexistentVocabularyName"
    ).should.throw(client.exceptions.BadRequestException)


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    client.create_medical_vocabulary.when.called_with(**args).should.throw(
        client.exceptions.ConflictException
    )


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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    client.create_vocabulary.when.called_with(**args).should.throw(
        client.exceptions.ConflictException
    )


@mock_transcribe
def test_create_vocabulary_with_bad_request():

    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    vocabulary_name = "MyVocabulary"
    args = {
        "VocabularyName": vocabulary_name,
        "LanguageCode": "en-US",
    }
    client.create_vocabulary.when.called_with(**args).should.throw(
        client.exceptions.BadRequestException
    )
    args = {
        "VocabularyName": vocabulary_name,
        "Phrases": [],
        "LanguageCode": "en-US",
    }
    client.create_vocabulary.when.called_with(**args).should.throw(
        client.exceptions.BadRequestException
    )
