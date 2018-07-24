from moto.core import BaseBackend


class ElastictranscoderBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(ElastictranscoderBackend, self).__init__()
        self.region_name = region_name


available_regions = ['us-east-1']
elastictranscoder_backends = {region: ElastictranscoderBackend(region) for region in available_regions}
