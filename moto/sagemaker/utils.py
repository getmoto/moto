from moto.s3.models import s3_backends
import json


def load_pipeline_definition_from_s3(pipeline_definition_s3_location, account_id):
    s3_backend = s3_backends[account_id]["global"]
    result = s3_backend.get_object(
        bucket_name=pipeline_definition_s3_location["Bucket"],
        key_name=pipeline_definition_s3_location["ObjectKey"],
    )
    return json.loads(result.value)


def arn_formatter(_type, _id, account_id, region_name):
    return f"arn:aws:sagemaker:{region_name}:{account_id}:{_type}/{_id}"
