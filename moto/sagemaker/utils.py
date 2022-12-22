import boto3
import json


def load_pipeline_definition_from_s3(pipeline_definition_s3_location):
    client = boto3.client("s3")
    result = client.get_object(
        Bucket=pipeline_definition_s3_location["Bucket"],
        Key=pipeline_definition_s3_location["ObjectKey"],
    )
    pipeline_definition = json.loads(result["Body"].read())
    return pipeline_definition


def arn_formatter(_type, _id, account_id, region_name):
    return f"arn:aws:sagemaker:{region_name}:{account_id}:{_type}/{_id}"
