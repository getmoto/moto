from .responses import InstanceMetadataResponse

url_bases = ["http://169.254.169.254"]

instance_metadata = InstanceMetadataResponse()

url_paths = {"{0}/(?P<path>.+)": instance_metadata.metadata_response}
