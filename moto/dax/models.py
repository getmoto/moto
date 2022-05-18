"""DAXBackend class with methods for supported APIs."""
from moto.core import get_account_id, BaseBackend, BaseModel
from moto.core.utils import BackendDict, get_random_hex, unix_time
from moto.moto_api import state_manager
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.tagging_service import TaggingService
from moto.utilities.paginator import paginate

from .exceptions import ClusterNotFoundFault
from .utils import PAGINATION_MODEL


class DaxParameterGroup(BaseModel):
    def __init__(self):
        self.name = "default.dax1.0"
        self.status = "in-sync"

    def to_json(self):
        return {
            "ParameterGroupName": self.name,
            "ParameterApplyStatus": self.status,
            "NodeIdsToReboot": [],
        }


class DaxNode:
    def __init__(self, endpoint, name, index):
        self.node_id = f"{name}-{chr(ord('a')+index)}"  # name-a, name-b, etc
        self.node_endpoint = {
            "Address": f"{self.node_id}.{endpoint.cluster_hex}.nodes.dax-clusters.{endpoint.region}.amazonaws.com",
            "Port": endpoint.port,
        }
        self.create_time = unix_time()
        # AWS spreads nodes across zones, i.e. three nodes will probably end up in us-east-1a, us-east-1b, us-east-1c
        # For simplicity, we'll 'deploy' everything to us-east-1a
        self.availability_zone = f"{endpoint.region}a"
        self.status = "available"
        self.parameter_status = "in-sync"

    def to_json(self):
        return {
            "NodeId": self.node_id,
            "Endpoint": self.node_endpoint,
            "NodeCreateTime": self.create_time,
            "AvailabilityZone": self.availability_zone,
            "NodeStatus": self.status,
            "ParameterGroupStatus": self.parameter_status,
        }


class DaxEndpoint:
    def __init__(self, name, cluster_hex, region):
        self.name = name
        self.cluster_hex = cluster_hex
        self.region = region
        self.port = 8111

    def to_json(self, full=False):
        dct = {"Port": self.port}
        if full:
            dct[
                "Address"
            ] = f"{self.name}.{self.cluster_hex}.dax-clusters.{self.region}.amazonaws.com"
            dct["URL"] = f"dax://{dct['Address']}"
        return dct


class DaxCluster(BaseModel, ManagedState):
    def __init__(
        self,
        region,
        name,
        description,
        node_type,
        replication_factor,
        iam_role_arn,
        sse_specification,
    ):
        # Configure ManagedState
        super().__init__(
            model_name="dax::cluster",
            transitions=[("creating", "available"), ("deleting", "deleted")],
        )
        # Set internal properties
        self.name = name
        self.description = description
        self.arn = f"arn:aws:dax:{region}:{get_account_id()}:cache/{self.name}"
        self.node_type = node_type
        self.replication_factor = replication_factor
        self.cluster_hex = get_random_hex(6)
        self.endpoint = DaxEndpoint(
            name=name, cluster_hex=self.cluster_hex, region=region
        )
        self.nodes = [self._create_new_node(i) for i in range(0, replication_factor)]
        self.preferred_maintenance_window = "thu:23:30-fri:00:30"
        self.subnet_group = "default"
        self.iam_role_arn = iam_role_arn
        self.parameter_group = DaxParameterGroup()
        self.security_groups = [
            {"SecurityGroupIdentifier": f"sg-{get_random_hex(10)}", "Status": "active"}
        ]
        self.sse_specification = sse_specification

    def _create_new_node(self, idx):
        return DaxNode(endpoint=self.endpoint, name=self.name, index=idx)

    def increase_replication_factor(self, new_replication_factor):
        for idx in range(self.replication_factor, new_replication_factor):
            self.nodes.append(self._create_new_node(idx))
        self.replication_factor = new_replication_factor

    def decrease_replication_factor(self, new_replication_factor, node_ids_to_remove):
        if node_ids_to_remove:
            self.nodes = [n for n in self.nodes if n.node_id not in node_ids_to_remove]
        else:
            self.nodes = self.nodes[0:new_replication_factor]
        self.replication_factor = new_replication_factor

    def delete(self):
        self.status = "deleting"

    def is_deleted(self):
        return self.status == "deleted"

    def to_json(self):
        use_full_repr = self.status == "available"
        dct = {
            "ClusterName": self.name,
            "Description": self.description,
            "ClusterArn": self.arn,
            "TotalNodes": self.replication_factor,
            "ActiveNodes": 0,
            "NodeType": self.node_type,
            "Status": self.status,
            "ClusterDiscoveryEndpoint": self.endpoint.to_json(use_full_repr),
            "PreferredMaintenanceWindow": self.preferred_maintenance_window,
            "SubnetGroup": self.subnet_group,
            "IamRoleArn": self.iam_role_arn,
            "ParameterGroup": self.parameter_group.to_json(),
            "SSEDescription": {
                "Status": "ENABLED"
                if self.sse_specification.get("Enabled") is True
                else "DISABLED"
            },
            "ClusterEndpointEncryptionType": "NONE",
            "SecurityGroups": self.security_groups,
        }
        if use_full_repr:
            dct["Nodes"] = [n.to_json() for n in self.nodes]
        return dct


class DAXBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self._clusters = dict()
        self._tagger = TaggingService()

        state_manager.register_default_transition(
            model_name="dax::cluster", transition={"progression": "manual", "times": 4}
        )

    @property
    def clusters(self):
        self._clusters = {
            name: cluster
            for name, cluster in self._clusters.items()
            if cluster.status != "deleted"
        }
        return self._clusters

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_cluster(
        self,
        cluster_name,
        node_type,
        description,
        replication_factor,
        iam_role_arn,
        tags,
        sse_specification,
    ):
        """
        The following parameters are not yet processed:
        AvailabilityZones, SubnetGroupNames, SecurityGroups, PreferredMaintenanceWindow, NotificationTopicArn, ParameterGroupName, ClusterEndpointEncryptionType
        """
        cluster = DaxCluster(
            region=self.region_name,
            name=cluster_name,
            description=description,
            node_type=node_type,
            replication_factor=replication_factor,
            iam_role_arn=iam_role_arn,
            sse_specification=sse_specification,
        )
        self.clusters[cluster_name] = cluster
        self._tagger.tag_resource(cluster.arn, tags)
        return cluster

    def delete_cluster(self, cluster_name):
        if cluster_name not in self.clusters:
            raise ClusterNotFoundFault()
        self.clusters[cluster_name].delete()
        return self.clusters[cluster_name]

    @paginate(PAGINATION_MODEL)
    def describe_clusters(self, cluster_names):
        clusters = self.clusters
        if not cluster_names:
            cluster_names = clusters.keys()

        for name in cluster_names:
            if name in self.clusters:
                self.clusters[name].advance()

        # Clusters may have been deleted while advancing the states
        clusters = self.clusters
        for name in cluster_names:
            if name not in self.clusters:
                raise ClusterNotFoundFault(name)
        return [cluster for name, cluster in clusters.items() if name in cluster_names]

    def list_tags(self, resource_name):
        """
        Pagination is not yet implemented
        """
        # resource_name can be the name, or the full ARN
        name = resource_name.split("/")[-1]
        if name not in self.clusters:
            raise ClusterNotFoundFault()
        return self._tagger.list_tags_for_resource(self.clusters[name].arn)

    def increase_replication_factor(self, cluster_name, new_replication_factor):
        """
        The AvailabilityZones-parameter is not yet implemented
        """
        if cluster_name not in self.clusters:
            raise ClusterNotFoundFault()
        self.clusters[cluster_name].increase_replication_factor(new_replication_factor)
        return self.clusters[cluster_name]

    def decrease_replication_factor(
        self,
        cluster_name,
        new_replication_factor,
        node_ids_to_remove,
    ):
        """
        The AvailabilityZones-parameter is not yet implemented
        """
        if cluster_name not in self.clusters:
            raise ClusterNotFoundFault()
        self.clusters[cluster_name].decrease_replication_factor(
            new_replication_factor, node_ids_to_remove
        )
        return self.clusters[cluster_name]


dax_backends = BackendDict(DAXBackend, "dax")
