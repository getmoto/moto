from __future__ import unicode_literals

import datetime

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from .exceptions import BadRequestException

from .utils import get_network_id

FRAMEWORKS = [
    "HYPERLEDGER_FABRIC",
]

FRAMEWORKVERSIONS = [
    "1.2",
]

EDITIONS = [
    "STARTER",
    "STANDARD",
]


class ManagedBlockchainNetwork(BaseModel):
    def __init__(
        self,
        id,
        name,
        framework,
        frameworkversion,
        frameworkconfiguration,
        voting_policy,
        member_configuration,
        region,
        description=None,
    ):
        self.st = datetime.datetime.now(datetime.timezone.utc)
        self.id = id
        self.name = name
        self.description = description
        self.framework = framework
        self.frameworkversion = frameworkversion
        self.frameworkconfiguration = frameworkconfiguration
        self.voting_policy = voting_policy
        self.member_configuration = member_configuration
        self.region = region

    def to_dict(self):
        frameworkattributes = {
            "Fabric": {
                "OrderingServiceEndpoint": "orderer.{0}.managedblockchain.{1}.amazonaws.com:30001".format(
                    self.id, self.region
                ),
                "Edition": self.frameworkconfiguration["Fabric"]["Edition"],
            }
        }

        vpcendpointname = "com.amazonaws.{0}.managedblockchain.{1}".format(
            self.region, self.id
        )
        # Use iso_8601_datetime_with_milliseconds ?
        d = {
            "Id": self.id,
            "Name": self.name,
            "Framework": self.framework,
            "FrameworkVersion": self.frameworkversion,
            "FrameworkAttributes": frameworkattributes,
            "VpcEndpointServiceName": vpcendpointname,
            "VotingPolicy": self.voting_policy,
            "Status": "AVAILABLE",
            "CreationDate": self.st.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        }
        if self.description is not None:
            d["Description"] = self.description
        return d


class ManagedBlockchainBackend(BaseBackend):
    def __init__(self, region_name):
        self.networks = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_network(
        self,
        json_body,
    ):
        name = json_body["Name"]
        framework = json_body["Framework"]
        frameworkversion = json_body["FrameworkVersion"]
        frameworkconfiguration = json_body["FrameworkConfiguration"]
        voting_policy = json_body["VotingPolicy"]
        member_configuration = json_body["MemberConfiguration"]

        # Check framework
        if framework not in FRAMEWORKS:
            raise BadRequestException("CreateNetwork", "Invalid request body")

        # Check framework version
        if frameworkversion not in FRAMEWORKVERSIONS:
            raise BadRequestException(
                "CreateNetwork",
                "Invalid version {0} requested for framework HYPERLEDGER_FABRIC".format(
                    frameworkversion
                ),
            )

        # Check edition
        if frameworkconfiguration["Fabric"]["Edition"] not in EDITIONS:
            raise BadRequestException("CreateNetwork", "Invalid request body")

        ## Generate network ID
        network_id = get_network_id()

        self.networks[network_id] = ManagedBlockchainNetwork(
            id=network_id,
            name=name,
            framework=framework,
            frameworkversion=frameworkversion,
            frameworkconfiguration=frameworkconfiguration,
            voting_policy=voting_policy,
            member_configuration=member_configuration,
            region=self.region_name,
        )

    def list_networks(self):
        return self.networks.values()

    def get_network(self, network_id):
        return self.networks[network_id]



managedblockchain_backends = {}
for region in Session().get_available_regions("managedblockchain"):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
for region in Session().get_available_regions(
    "managedblockchain", partition_name="aws-us-gov"
):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
for region in Session().get_available_regions(
    "managedblockchain", partition_name="aws-cn"
):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
