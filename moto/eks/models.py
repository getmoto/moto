from __future__ import unicode_literals

from boto3 import Session
from moto.core import BaseBackend


class EKSBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(EKSBackend, self).__init__()
        self.clusters = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def list_clusters(self, max_results, next_token):
        cluster_names = sorted(self.clusters.keys())
        total_clusters = len(cluster_names)
        start = cluster_names.index(next_token) if next_token != '' else 0
        end = min(start + max_results, total_clusters)
        new_next = 'null' if end == total_clusters else cluster_names[end]

        return cluster_names[start:end], new_next
    

eks_backends = {}
for region in Session().get_available_regions("eks"):
    eks_backends[region] = EKSBackend()
for region in Session().get_available_regions("eks", partition_name="aws-us-gov"):
    eks_backends[region] = EKSBackend()
for region in Session().get_available_regions("eks", partition_name="aws-cn"):
    eks_backends[region] = EKSBackend()
