from __future__ import unicode_literals

import datetime
import re

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from .exceptions import (
    BadRequestException,
    ResourceNotFoundException,
    InvalidRequestException,
)

from .utils import get_network_id, get_member_id, get_proposal_id

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

    @property
    def vote_pol_proposal_duration(self):
        return self.voting_policy["ApprovalThresholdPolicy"]["ProposalDurationInHours"]

    @property
    def vote_pol_threshold_percentage(self):
        return self.voting_policy["ApprovalThresholdPolicy"]["ThresholdPercentage"]

    @property
    def vote_pol_threshold_comparator(self):
        return self.voting_policy["ApprovalThresholdPolicy"]["ThresholdComparator"]

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
        # Format for get_network
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


class ManagedBlockchainProposal(BaseModel):
    def __init__(
        self,
        id,
        networkid,
        memberid,
        membername,
        numofmembers,
        actions,
        network_expirtation,
        network_threshold,
        network_threshold_comp,
        description=None,
    ):
        # In general, passing all values instead of creating
        # an apparatus to look them up
        self.creationdate = datetime.datetime.utcnow()
        self.id = id
        self.networkid = networkid
        self.memberid = memberid
        self.membername = membername
        self.numofmembers = numofmembers
        self.actions = actions
        self.network_expirtation = network_expirtation
        self.network_threshold = network_threshold
        self.network_threshold_comp = network_threshold_comp
        self.description = description

        self.expirtationdate = self.creationdate + datetime.timedelta(
            hours=network_expirtation
        )
        self.yes_vote_count = 0
        self.no_vote_count = 0
        self.outstanding_vote_count = self.numofmembers
        self.status = "IN_PROGRESS"
        self.votes = {}

    @property
    def network_id(self):
        return self.networkid

    def to_dict(self):
        # Format for list_proposals
        d = {
            "ProposalId": self.id,
            "ProposedByMemberId": self.memberid,
            "ProposedByMemberName": self.membername,
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "ExpirationDate": self.expirtationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        }
        return d

    def get_format(self):
        # Format for get_proposal
        d = {
            "ProposalId": self.id,
            "NetworkId": self.networkid,
            "Actions": self.actions,
            "ProposedByMemberId": self.memberid,
            "ProposedByMemberName": self.membername,
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "ExpirationDate": self.expirtationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "YesVoteCount": self.yes_vote_count,
            "NoVoteCount": self.no_vote_count,
            "OutstandingVoteCount": self.outstanding_vote_count,
        }
        if self.description is not None:
            d["Description"] = self.description
        return d

    def set_vote(self, votermemberid, votermembername, vote):
        if self.status != "IN_PROGRESS":
            # Already decided
            return

        if datetime.datetime.utcnow() > self.expirtationdate:
            self.status = "EXPIRED"
            return

        if vote.lower() == "yes":
            self.yes_vote_count += 1
        else:
            self.no_vote_count += 1
        self.outstanding_vote_count -= 1

        perct_yes = (self.yes_vote_count / self.numofmembers) * 100
        perct_no = (self.no_vote_count / self.numofmembers) * 100
        self.votes[votermemberid] = {
            "MemberId ": votermemberid,
            "MemberName": votermembername,
            "Vote": vote.upper(),
        }

        if self.network_threshold_comp == "GREATER_THAN_OR_EQUAL_TO":
            if perct_yes >= self.network_threshold:
                self.status = "APPROVED"
            elif perct_no >= self.network_threshold:
                self.status = "REJECTED"
        else:
            if perct_yes > self.network_threshold:
                self.status = "APPROVED"
            elif perct_no > self.network_threshold:
                self.status = "REJECTED"


class ManagedBlockchainMember(BaseModel):
    def __init__(
        self, id, networkid, member_configuration, region,
    ):
        self.creationdate = datetime.datetime.utcnow()
        self.id = id
        self.networkid = networkid
        self.member_configuration = member_configuration
        self.status = "AVAILABLE"
        self.region = region

    @property
    def network_id(self):
        return self.networkid

    @property
    def name(self):
        return self.member_configuration["Name"]

    def to_dict(self):
        # Format for list_members
        d = {
            "Id": self.id,
            "Name": self.member_configuration["Name"],
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "IsOwned": True,
        }
        if "Description" in self.member_configuration:
            self.member_configuration["Description"] = self.description
        return d

    def get_format(self):
        # Format for get_member
        frameworkattributes = {
            "Fabric": {
                "AdminUsername": self.member_configuration["FrameworkConfiguration"][
                    "Fabric"
                ]["AdminUsername"],
                "CaEndpoint": "ca.{0}.{1}.managedblockchain.{2}.amazonaws.com:30002".format(
                    self.id.lower(), self.networkid.lower(), self.region
                ),
            }
        }

        d = {
            "NetworkId": self.networkid,
            "Id": self.id,
            "Name": self.name,
            "FrameworkAttributes": frameworkattributes,
            "LogPublishingConfiguration": self.member_configuration[
                "LogPublishingConfiguration"
            ],
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        }
        if "Description" in self.member_configuration:
            d["Description"] = self.description
        return d


class ManagedBlockchainBackend(BaseBackend):
    def __init__(self, region_name):
        self.networks = {}
        self.members = {}
        self.proposals = {}
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

        ## Generate memberid ID and initial member
        member_id = get_member_id()
        self.members[member_id] = ManagedBlockchainMember(
            id=member_id,
            networkid=network_id,
            member_configuration=member_configuration,
            region=self.region_name,
        )

        self.networks[network_id] = ManagedBlockchainNetwork(
            id=network_id,
            name=name,
            framework=framework,
            frameworkversion=frameworkversion,
            frameworkconfiguration=frameworkconfiguration,
            voting_policy=voting_policy,
            member_configuration=member_configuration,
            region=self.region_name,
            description=description,
        )

        # Return the network and member ID
        d = {"NetworkId": network_id, "MemberId": member_id}
        return d

    def list_networks(self):
        return self.networks.values()

    def get_network(self, network_id):
        if network_id not in self.networks:
            raise ResourceNotFoundException(
                "GetNetwork", "Network {0} not found.".format(network_id)
            )
        return self.networks.get(network_id)

    def create_proposal(
        self, networkid, memberid, actions, description=None,
    ):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "CreateProposal", "Network {0} not found.".format(networkid)
            )

        # Check if member exists
        if memberid not in self.members:
            raise ResourceNotFoundException(
                "CreateProposal", "Member {0} not found.".format(memberid)
            )

        # TODO Handle Removals
        # TODO Cannot have both Invitations and Removals
        # Invitations is an array, not sure if mutiple could actually be sent
        if re.match("[0-9]{12}", actions["Invitations"][0]["Principal"]) is None:
            raise InvalidRequestException(
                "CreateProposal",
                "Account ID format specified in proposal is not valid.",
            )

        ## Generate proposal ID
        proposal_id = get_proposal_id()

        self.proposals[proposal_id] = ManagedBlockchainProposal(
            id=proposal_id,
            networkid=networkid,
            memberid=memberid,
            membername=self.members.get(memberid).name,
            numofmembers=len(
                [
                    membid
                    for membid in self.members
                    if self.members.get(membid).network_id == networkid
                ]
            ),
            actions=actions,
            network_expirtation=self.networks.get(networkid).vote_pol_proposal_duration,
            network_threshold=self.networks.get(networkid).vote_pol_threshold_percentage,
            network_threshold_comp=self.networks.get(networkid).vote_pol_threshold_comparator,
            description=description,
        )

        # Return the proposal ID
        d = {"ProposalId": proposal_id}
        return d

    def list_proposals(self, networkid):
        proposalsfornetwork = []
        for proposal_id in self.proposals:
            if self.proposals.get(proposal_id).network_id == networkid:
                proposalsfornetwork.append(self.proposals[proposal_id])
        return proposalsfornetwork

    def get_proposal(self, networkid, proposalid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "GetProposal", "Network {0} not found.".format(networkid)
            )

        if proposalid not in self.proposals:
            raise ResourceNotFoundException(
                "GetProposal", "Proposal {0} not found.".format(proposalid)
            )
        return self.proposals.get(proposalid)


managedblockchain_backends = {}
for region in Session().get_available_regions("managedblockchain"):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
