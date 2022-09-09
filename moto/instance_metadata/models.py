from moto.core import BaseBackend
from moto.core.utils import BackendDict


class InstanceMetadataBackend(BaseBackend):
    pass


instance_metadata_backends = BackendDict(
    InstanceMetadataBackend,
    "instance_metadata",
    use_boto3_regions=False,
    additional_regions=["global"],
)
