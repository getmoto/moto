from moto.s3.models import s3_backends
from moto import settings
import json
import boto3


def load_pipeline_definition_from_s3(pipeline_definition_s3_location, account_id):
    if settings.TEST_SERVER_MODE:
        # In ServerMode, we must get the object via boto3
        s3_client = boto3.client("s3")
        result = s3_client.get_object(
            Bucket=pipeline_definition_s3_location["Bucket"],
            Key=pipeline_definition_s3_location["ObjectKey"],
        )
        pipeline_definition_raw = result["Body"].read()
    else:
        # Otherwise, we can fetch it directly from the s3_backend
        s3_backend = s3_backends[account_id]["global"]
        result = s3_backend.get_object(
            bucket_name=pipeline_definition_s3_location["Bucket"],
            key_name=pipeline_definition_s3_location["ObjectKey"],
        )
        pipeline_definition_raw = result.value
    return json.loads(pipeline_definition_raw)


def arn_formatter(_type, _id, account_id, region_name):
    return f"arn:aws:sagemaker:{region_name}:{account_id}:{_type}/{_id}"
