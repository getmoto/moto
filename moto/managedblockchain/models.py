from __future__ import unicode_literals

import datetime

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from .exceptions import BadRequestException, ResourceNotFoundException

from .utils import get_network_id, get_member_id

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
        self.creationdate = datetime.datetime.utcnow()
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
        # Format for list_networks
        d = {
            "Id": self.id,
            "Name": self.name,
            "Framework": self.framework,
            "FrameworkVersion": self.frameworkversion,
            "Status": "AVAILABLE",
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        }
        if self.description is not None:
            d["Description"] = self.description
        return d

    def get_format(self):
        # Format for get_networks
        frameworkattributes = {
            "Fabric": {
                "OrderingServiceEndpoint": "orderer.{0}.managedblockchain.{1}.amazonaws.com:30001".format(
                    self.id.lower(), self.region
                ),
                "Edition": self.frameworkconfiguration["Fabric"]["Edition"],
            }
        }

        vpcendpointname = "com.amazonaws.{0}.managedblockchain.{1}".format(
            self.region, self.id.lower()
        )

        d = {
            "Id": self.id,
            "Name": self.name,
            "Framework": self.framework,
            "FrameworkVersion": self.frameworkversion,
            "FrameworkAttributes": frameworkattributes,
            "VpcEndpointServiceName": vpcendpointname,
            "VotingPolicy": self.voting_policy,
            "Status": "AVAILABLE",
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
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
        name,
        framework,
        frameworkversion,
        frameworkconfiguration,
        voting_policy,
        member_configuration,
        description=None,
    ):
        self.name = name
        self.framework = framework
        self.frameworkversion = frameworkversion
        self.frameworkconfiguration = frameworkconfiguration
        self.voting_policy = voting_policy
        self.member_configuration = member_configuration
        self.description = description

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

        ## Generate memberid ID - will need to actually create member
        member_id = get_member_id()

        self.networks[network_id] = ManagedBlockchainNetwork(
            id=network_id,
            name=name,
            framework=self.framework,
            frameworkversion=self.frameworkversion,
            frameworkconfiguration=self.frameworkconfiguration,
            voting_policy=self.voting_policy,
            member_configuration=self.member_configuration,
            region=self.region_name,
            description=self.description,
        )

        # Return the network and member ID
        d = {"NetworkId": network_id, "MemberId": member_id}
        return d

    def list_networks(self):
        return self.networks.values()

    def get_network(self, network_id):
        if network_id not in self.networks:
            raise ResourceNotFoundException(
                "CreateNetwork", "Network {0} not found".format(network_id)
            )
        return self.networks.get(network_id)


managedblockchain_backends = {}
for region in Session().get_available_regions("managedblockchain"):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
