"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_bedrock import BedrockClient, BedrockConfig
    from aws_sdk_bedrock.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-bedrock is not installed", allow_module_level=True)


@mock_aws
def test_fine_tune_foundation_model():
    """Enable invocation logging, fine-tune a foundation model, then clean up the custom model."""
    config = BedrockConfig.resolve(region="us-east-1")
    suffix = str(uuid4())[:8]
    job_name = f"support-bot-job-{suffix}"
    model_name = f"support-bot-{suffix}"
    role_arn = "arn:aws:iam::123456789012:role/BedrockFineTuning"

    with BedrockClient(config=config) as client:
        client.put_model_invocation_logging_configuration(
            logging_config={
                "s3_config": {
                    "bucket_name": "invocation-logs",
                    "key_prefix": "bedrock",
                },
                "text_data_delivery_enabled": True,
            }
        )
        logging = client.get_model_invocation_logging_configuration().logging_config
        assert logging.s3_config.bucket_name == "invocation-logs"
        assert logging.s3_config.key_prefix == "bedrock"

        job_arn = client.create_model_customization_job(
            job_name=job_name,
            custom_model_name=model_name,
            role_arn=role_arn,
            base_model_identifier="amazon.titan-text-express-v1",
            customization_type="FINE_TUNING",
            training_data_config={"s3_uri": "s3://training-data/support.jsonl"},
            output_data_config={"s3_uri": "s3://training-output/"},
            hyper_parameters={"epochCount": "2", "learningRate": "0.00001"},
            custom_model_tags=[{"key": "team", "value": "support"}],
        ).job_arn
        assert job_arn.endswith(f":model-customization-job/{job_name}")

        job = client.get_model_customization_job(job_identifier=job_name)
        assert job.status == "InProgress"
        assert job.role_arn == role_arn
        assert job.hyper_parameters == {"epochCount": "2", "learningRate": "0.00001"}

        jobs = client.list_model_customization_jobs(name_contains=suffix)
        assert [j.job_name for j in jobs.model_customization_job_summaries] == [
            job_name
        ]

        client.stop_model_customization_job(job_identifier=job_name)
        job = client.get_model_customization_job(job_identifier=job_name)
        assert job.status == "Stopped"

        model = client.get_custom_model(model_identifier=model_name)
        assert model.model_name == model_name
        assert model.job_arn == job_arn
        assert model.base_model_arn.endswith(
            "foundation-model/amazon.titan-text-express-v1"
        )

        tags = client.list_tags_for_resource(resource_arn=model.model_arn).tags
        assert [(t.key, t.value) for t in tags] == [("team", "support")]

        client.delete_custom_model(model_identifier=model_name)
        models = client.list_custom_models().model_summaries
        assert model_name not in [m.model_name for m in models]
        with pytest.raises(ResourceNotFoundException):
            client.get_custom_model(model_identifier=model_name)
