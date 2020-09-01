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
            "VocabularyName": "MyMedicalVocabulary",
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
def test_get_nonexistent_medical_transcription_job():
    region_name = "us-east-1"
    client = boto3.client("transcribe", region_name=region_name)

    client.get_medical_transcription_job.when.called_with(
        MedicalTranscriptionJobName="NonexistentJobName"
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
