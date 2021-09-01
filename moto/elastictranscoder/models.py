from __future__ import unicode_literals
from boto3 import Session
from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
import random
import string


class Pipeline(BaseModel):
    def __init__(
        self,
        region,
        name,
        input_bucket,
        output_bucket,
        role,
        content_config,
        thumbnail_config,
    ):
        a = "".join(random.choice(string.digits) for _ in range(13))
        b = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
        self.id = "{}-{}".format(a, b)
        self.name = name
        self.arn = "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, self.id
        )
        self.status = "Active"
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket or content_config["Bucket"]
        self.role = role
        self.content_config = content_config or {"Bucket": self.output_bucket}
        if "Permissions" not in self.content_config:
            self.content_config["Permissions"] = []
        self.thumbnail_config = thumbnail_config or {"Bucket": self.output_bucket}
        if "Permissions" not in self.thumbnail_config:
            self.thumbnail_config["Permissions"] = []

    def update(self, name, input_bucket, role):
        if name:
            self.name = name
        if input_bucket:
            self.input_bucket = input_bucket
        if role:
            self.role = role

    def to_dict(self):
        return {
            "Id": self.id,
            "Name": self.name,
            "Arn": self.arn,
            "Status": self.status,
            "InputBucket": self.input_bucket,
            "OutputBucket": self.output_bucket,
            "Role": self.role,
            "Notifications": {
                "Progressing": "",
                "Completed": "",
                "Warning": "",
                "Error": "",
            },
            "ContentConfig": self.content_config,
            "ThumbnailConfig": self.thumbnail_config,
        }


class ElasticTranscoderBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(ElasticTranscoderBackend, self).__init__()
        self.region_name = region_name
        self.pipelines = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_pipeline(
        self,
        name,
        input_bucket,
        output_bucket,
        role,
        aws_kms_key_arn,
        notifications,
        content_config,
        thumbnail_config,
    ):
        pipeline = Pipeline(
            self.region_name,
            name,
            input_bucket,
            output_bucket,
            role,
            content_config,
            thumbnail_config,
        )
        self.pipelines[pipeline.id] = pipeline
        warnings = []
        return pipeline, warnings

    def list_pipelines(self):
        return [p.to_dict() for _, p in self.pipelines.items()]

    def read_pipeline(self, id):
        return self.pipelines[id]

    def update_pipeline(
        self,
        id,
        name,
        input_bucket,
        role,
        aws_kms_key_arn,
        notifications,
        content_config,
        thumbnail_config,
    ):
        pipeline = self.read_pipeline(id)
        pipeline.update(name, input_bucket, role)
        warnings = []
        return pipeline, warnings

    def delete_pipeline(self, pipeline_id):
        self.pipelines.pop(pipeline_id)


elastictranscoder_backends = {}
for region in Session().get_available_regions("elastictranscoder"):
    elastictranscoder_backends[region] = ElasticTranscoderBackend(region)
for region in Session().get_available_regions(
    "elastictranscoder", partition_name="aws-us-gov"
):
    elastictranscoder_backends[region] = ElasticTranscoderBackend(region)
for region in Session().get_available_regions(
    "elastictranscoder", partition_name="aws-cn"
):
    elastictranscoder_backends[region] = ElasticTranscoderBackend(region)
