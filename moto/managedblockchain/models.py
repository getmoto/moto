from __future__ import division

import datetime
import re

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict

from .exceptions import (
    BadRequestException,
    ResourceNotFoundException,
    InvalidRequestException,
    ResourceLimitExceededException,
    ResourceAlreadyExistsException,
)

from .utils import (
    get_network_id,
    get_member_id,
    get_proposal_id,
    get_invitation_id,
    member_name_exist_in_network,
    number_of_members_in_network,
    admin_password_ok,
    get_node_id,
    number_of_nodes_in_member,
    nodes_in_member,
)

FRAMEWORKS = [
    "HYPERLEDGER_FABRIC",
]

FRAMEWORKVERSIONS = [
    "1.2",
]

EDITIONS = {
    "STARTER": {
        "MaxMembers": 5,
        "MaxNodesPerMember": 2,
        "AllowedNodeInstanceTypes": ["bc.t3.small", "bc.t3.medium"],
    },
    "STANDARD": {
        "MaxMembers": 14,
        "MaxNodesPerMember": 3,
        "AllowedNodeInstanceTypes": ["bc.t3", "bc.m5", "bc.c5"],
    },
}

VOTEVALUES = ["YES", "NO"]


class ManagedBlockchainNetwork(BaseModel):
    def __init__(
        self,
        network_id,
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
        self.id = network_id
        self.name = name
        self.description = description
        self.framework = framework
        self.frameworkversion = frameworkversion
        self.frameworkconfiguration = frameworkconfiguration
        self.voting_policy = voting_policy
        self.member_configuration = member_configuration
        self.region = region

    @property
    def network_name(self):
        return self.name

    @property
    def network_framework(self):
        return self.framework

    @property
    def network_framework_version(self):
        return self.frameworkversion

    @property
    def network_creationdate(self):
        return self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z")

    @property
    def network_description(self):
        return self.description

    @property
    def network_edition(self):
        return self.frameworkconfiguration["Fabric"]["Edition"]

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
        proposal_id,
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
        self.id = proposal_id
        self.networkid = networkid
        self.memberid = memberid
        self.membername = membername
        self.numofmembers = numofmembers
        self.actions = actions
        self.network_expirtation = network_expirtation
        self.network_threshold = network_threshold
        self.network_threshold_comp = network_threshold_comp
        self.description = description

        self.creationdate = datetime.datetime.utcnow()
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

    @property
    def proposal_status(self):
        return self.status

    @property
    def proposal_votes(self):
        return self.votes

    def proposal_actions(self, action_type):
        default_return = []
        if action_type.lower() == "invitations":
            if "Invitations" in self.actions:
                return self.actions["Invitations"]
        elif action_type.lower() == "removals":
            if "Removals" in self.actions:
                return self.actions["Removals"]
        return default_return

    def check_to_expire_proposal(self):
        if datetime.datetime.utcnow() > self.expirtationdate:
            self.status = "EXPIRED"

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
        if vote.upper() == "YES":
            self.yes_vote_count += 1
        else:
            self.no_vote_count += 1
        self.outstanding_vote_count -= 1

        perct_yes = (self.yes_vote_count / self.numofmembers) * 100
        perct_no = (self.no_vote_count / self.numofmembers) * 100
        self.votes[votermemberid] = {
            "MemberId": votermemberid,
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

        # It is a tie - reject
        if (
            self.status == "IN_PROGRESS"
            and self.network_threshold_comp == "GREATER_THAN"
            and self.outstanding_vote_count == 0
            and perct_yes == perct_no
        ):
            self.status = "REJECTED"


class ManagedBlockchainInvitation(BaseModel):
    def __init__(
        self,
        invitation_id,
        networkid,
        networkname,
        networkframework,
        networkframeworkversion,
        networkcreationdate,
        region,
        networkdescription=None,
    ):
        self.id = invitation_id
        self.networkid = networkid
        self.networkname = networkname
        self.networkdescription = networkdescription
        self.networkframework = networkframework
        self.networkframeworkversion = networkframeworkversion
        self.networkstatus = "AVAILABLE"
        self.networkcreationdate = networkcreationdate
        self.status = "PENDING"
        self.region = region

        self.creationdate = datetime.datetime.utcnow()
        self.expirtationdate = self.creationdate + datetime.timedelta(days=7)

    @property
    def invitation_status(self):
        return self.status

    @property
    def invitation_networkid(self):
        return self.networkid

    def to_dict(self):
        d = {
            "InvitationId": self.id,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "ExpirationDate": self.expirtationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "Status": self.status,
            "NetworkSummary": {
                "Id": self.networkid,
                "Name": self.networkname,
                "Framework": self.networkframework,
                "FrameworkVersion": self.networkframeworkversion,
                "Status": self.networkstatus,
                "CreationDate": self.networkcreationdate,
            },
        }
        if self.networkdescription is not None:
            d["NetworkSummary"]["Description"] = self.networkdescription
        return d

    def accept_invitation(self):
        self.status = "ACCEPTED"

    def reject_invitation(self):
        self.status = "REJECTED"

    def set_network_status(self, network_status):
        self.networkstatus = network_status


class ManagedBlockchainMember(BaseModel):
    def __init__(
        self, member_id, networkid, member_configuration, region,
    ):
        self.creationdate = datetime.datetime.utcnow()
        self.id = member_id
        self.networkid = networkid
        self.member_configuration = member_configuration
        self.status = "AVAILABLE"
        self.region = region
        self.description = None

    @property
    def network_id(self):
        return self.networkid

    @property
    def name(self):
        return self.member_configuration["Name"]

    @property
    def member_status(self):
        return self.status

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
            self.description = self.member_configuration["Description"]
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

    def delete(self):
        self.status = "DELETED"

    def update(self, logpublishingconfiguration):
        self.member_configuration[
            "LogPublishingConfiguration"
        ] = logpublishingconfiguration


class ManagedBlockchainNode(BaseModel):
    def __init__(
        self,
        node_id,
        networkid,
        memberid,
        availabilityzone,
        instancetype,
        logpublishingconfiguration,
        region,
    ):
        self.creationdate = datetime.datetime.utcnow()
        self.id = node_id
        self.instancetype = instancetype
        self.networkid = networkid
        self.memberid = memberid
        self.logpublishingconfiguration = logpublishingconfiguration
        self.region = region
        self.status = "AVAILABLE"
        self.availabilityzone = availabilityzone

    @property
    def member_id(self):
        return self.memberid

    @property
    def node_status(self):
        return self.status

    def to_dict(self):
        # Format for list_nodes
        d = {
            "Id": self.id,
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "AvailabilityZone": self.availabilityzone,
            "InstanceType": self.instancetype,
        }
        return d

    def get_format(self):
        # Format for get_node
        frameworkattributes = {
            "Fabric": {
                "PeerEndpoint": "{0}.{1}.{2}.managedblockchain.{3}.amazonaws.com:30003".format(
                    self.id.lower(),
                    self.networkid.lower(),
                    self.memberid.lower(),
                    self.region,
                ),
                "PeerEventEndpoint": "{0}.{1}.{2}.managedblockchain.{3}.amazonaws.com:30004".format(
                    self.id.lower(),
                    self.networkid.lower(),
                    self.memberid.lower(),
                    self.region,
                ),
            }
        }

        d = {
            "NetworkId": self.networkid,
            "MemberId": self.memberid,
            "Id": self.id,
            "InstanceType": self.instancetype,
            "AvailabilityZone": self.availabilityzone,
            "FrameworkAttributes": frameworkattributes,
            "LogPublishingConfiguration": self.logpublishingconfiguration,
            "Status": self.status,
            "CreationDate": self.creationdate.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        }
        return d

    def delete(self):
        self.status = "DELETED"

    def update(self, logpublishingconfiguration):
        self.logpublishingconfiguration = logpublishingconfiguration


class ManagedBlockchainBackend(BaseBackend):
    def __init__(self, region_name):
        self.networks = {}
        self.members = {}
        self.proposals = {}
        self.invitations = {}
        self.nodes = {}
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

        # Generate network ID
        network_id = get_network_id()

        # Generate memberid ID and initial member
        member_id = get_member_id()
        self.members[member_id] = ManagedBlockchainMember(
            member_id=member_id,
            networkid=network_id,
            member_configuration=member_configuration,
            region=self.region_name,
        )

        self.networks[network_id] = ManagedBlockchainNetwork(
            network_id=network_id,
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

        # CLI docs say that Invitations and Removals cannot both be passed - but it does
        # not throw an error and can be performed
        if "Invitations" in actions:
            for propinvitation in actions["Invitations"]:
                if re.match("[0-9]{12}", propinvitation["Principal"]) is None:
                    raise InvalidRequestException(
                        "CreateProposal",
                        "Account ID format specified in proposal is not valid.",
                    )

        if "Removals" in actions:
            for propmember in actions["Removals"]:
                if propmember["MemberId"] not in self.members:
                    raise InvalidRequestException(
                        "CreateProposal",
                        "Member ID format specified in proposal is not valid.",
                    )

        # Generate proposal ID
        proposal_id = get_proposal_id()

        self.proposals[proposal_id] = ManagedBlockchainProposal(
            proposal_id=proposal_id,
            networkid=networkid,
            memberid=memberid,
            membername=self.members.get(memberid).name,
            numofmembers=number_of_members_in_network(self.members, networkid),
            actions=actions,
            network_expirtation=self.networks.get(networkid).vote_pol_proposal_duration,
            network_threshold=self.networks.get(
                networkid
            ).vote_pol_threshold_percentage,
            network_threshold_comp=self.networks.get(
                networkid
            ).vote_pol_threshold_comparator,
            description=description,
        )

        # Return the proposal ID
        d = {"ProposalId": proposal_id}
        return d

    def list_proposals(self, networkid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "ListProposals", "Network {0} not found.".format(networkid)
            )

        proposalsfornetwork = []
        for proposal_id in self.proposals:
            if self.proposals.get(proposal_id).network_id == networkid:
                # See if any are expired
                self.proposals.get(proposal_id).check_to_expire_proposal()
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

        # See if it needs to be set to expipred
        self.proposals.get(proposalid).check_to_expire_proposal()
        return self.proposals.get(proposalid)

    def vote_on_proposal(self, networkid, proposalid, votermemberid, vote):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "VoteOnProposal", "Network {0} not found.".format(networkid)
            )

        if proposalid not in self.proposals:
            raise ResourceNotFoundException(
                "VoteOnProposal", "Proposal {0} not found.".format(proposalid)
            )

        if votermemberid not in self.members:
            raise ResourceNotFoundException(
                "VoteOnProposal", "Member {0} not found.".format(votermemberid)
            )

        if vote.upper() not in VOTEVALUES:
            raise BadRequestException("VoteOnProposal", "Invalid request body")

        # See if it needs to be set to expipred
        self.proposals.get(proposalid).check_to_expire_proposal()

        # Exception if EXPIRED
        if self.proposals.get(proposalid).proposal_status == "EXPIRED":
            raise InvalidRequestException(
                "VoteOnProposal",
                "Proposal {0} is expired and you cannot vote on it.".format(proposalid),
            )

        # Check if IN_PROGRESS
        if self.proposals.get(proposalid).proposal_status != "IN_PROGRESS":
            raise InvalidRequestException(
                "VoteOnProposal",
                "Proposal {0} has status {1} and you cannot vote on it.".format(
                    proposalid, self.proposals.get(proposalid).proposal_status
                ),
            )

        # Check to see if this member already voted
        if votermemberid in self.proposals.get(proposalid).proposal_votes:
            raise ResourceAlreadyExistsException(
                "VoteOnProposal",
                "Member {0} has already voted on proposal {1}.".format(
                    votermemberid, proposalid
                ),
            )

        # Cast vote
        self.proposals.get(proposalid).set_vote(
            votermemberid, self.members.get(votermemberid).name, vote.upper()
        )

        if self.proposals.get(proposalid).proposal_status == "APPROVED":
            # Generate invitations
            for _ in self.proposals.get(proposalid).proposal_actions("Invitations"):
                invitation_id = get_invitation_id()
                self.invitations[invitation_id] = ManagedBlockchainInvitation(
                    invitation_id=invitation_id,
                    networkid=networkid,
                    networkname=self.networks.get(networkid).network_name,
                    networkframework=self.networks.get(networkid).network_framework,
                    networkframeworkversion=self.networks.get(
                        networkid
                    ).network_framework_version,
                    networkcreationdate=self.networks.get(
                        networkid
                    ).network_creationdate,
                    region=self.region_name,
                    networkdescription=self.networks.get(networkid).network_description,
                )

            # Delete members
            for propmember in self.proposals.get(proposalid).proposal_actions(
                "Removals"
            ):
                self.delete_member(networkid, propmember["MemberId"])

    def list_proposal_votes(self, networkid, proposalid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "ListProposalVotes", "Network {0} not found.".format(networkid)
            )

        if proposalid not in self.proposals:
            raise ResourceNotFoundException(
                "ListProposalVotes", "Proposal {0} not found.".format(proposalid)
            )

        # Output the vote summaries
        proposalvotesfornetwork = []
        for proposal_id in self.proposals:
            if self.proposals.get(proposal_id).network_id == networkid:
                for pvmemberid in self.proposals.get(proposal_id).proposal_votes:
                    proposalvotesfornetwork.append(
                        self.proposals.get(proposal_id).proposal_votes[pvmemberid]
                    )
        return proposalvotesfornetwork

    def list_invitations(self):
        return self.invitations.values()

    def reject_invitation(self, invitationid):
        if invitationid not in self.invitations:
            raise ResourceNotFoundException(
                "RejectInvitation", "InvitationId {0} not found.".format(invitationid)
            )
        self.invitations.get(invitationid).reject_invitation()

    def create_member(
        self, invitationid, networkid, member_configuration,
    ):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "CreateMember", "Network {0} not found.".format(networkid)
            )

        if invitationid not in self.invitations:
            raise InvalidRequestException(
                "CreateMember", "Invitation {0} not valid".format(invitationid)
            )

        if self.invitations.get(invitationid).invitation_status != "PENDING":
            raise InvalidRequestException(
                "CreateMember", "Invitation {0} not valid".format(invitationid)
            )

        if (
            member_name_exist_in_network(
                self.members, networkid, member_configuration["Name"]
            )
            is True
        ):
            raise InvalidRequestException(
                "CreateMember",
                "Member name {0} already exists in network {1}.".format(
                    member_configuration["Name"], networkid
                ),
            )

        networkedition = self.networks.get(networkid).network_edition
        if (
            number_of_members_in_network(self.members, networkid)
            >= EDITIONS[networkedition]["MaxMembers"]
        ):
            raise ResourceLimitExceededException(
                "CreateMember",
                "You cannot create a member in network {0}.{1} is the maximum number of members allowed in a {2} Edition network.".format(
                    networkid, EDITIONS[networkedition]["MaxMembers"], networkedition
                ),
            )

        memberadminpassword = member_configuration["FrameworkConfiguration"]["Fabric"][
            "AdminPassword"
        ]
        if admin_password_ok(memberadminpassword) is False:
            raise BadRequestException("CreateMember", "Invalid request body")

        member_id = get_member_id()
        self.members[member_id] = ManagedBlockchainMember(
            member_id=member_id,
            networkid=networkid,
            member_configuration=member_configuration,
            region=self.region_name,
        )

        # Accept the invitaiton
        self.invitations.get(invitationid).accept_invitation()

        # Return the member ID
        d = {"MemberId": member_id}
        return d

    def list_members(self, networkid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "ListMembers", "Network {0} not found.".format(networkid)
            )

        membersfornetwork = []
        for member_id in self.members:
            if self.members.get(member_id).network_id == networkid:
                membersfornetwork.append(self.members[member_id])
        return membersfornetwork

    def get_member(self, networkid, memberid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "GetMember", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "GetMember", "Member {0} not found.".format(memberid)
            )

        # Cannot get a member than has been deleted (it does show up in the list)
        if self.members.get(memberid).member_status == "DELETED":
            raise ResourceNotFoundException(
                "GetMember", "Member {0} not found.".format(memberid)
            )

        return self.members.get(memberid)

    def delete_member(self, networkid, memberid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "DeleteMember", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "DeleteMember", "Member {0} not found.".format(memberid)
            )

        self.members.get(memberid).delete()

        # Is this the last member in the network? (all set to DELETED)
        if number_of_members_in_network(
            self.members, networkid, member_status="DELETED"
        ) == len(self.members):
            # Set network status to DELETED for all invitations
            for invitation_id in self.invitations:
                if (
                    self.invitations.get(invitation_id).invitation_networkid
                    == networkid
                ):
                    self.invitations.get(invitation_id).set_network_status("DELETED")

            # Remove network
            del self.networks[networkid]

        # Remove any nodes associated
        for nodeid in nodes_in_member(self.nodes, memberid):
            del self.nodes[nodeid]

    def update_member(self, networkid, memberid, logpublishingconfiguration):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "UpdateMember", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "UpdateMember", "Member {0} not found.".format(memberid)
            )

        self.members.get(memberid).update(logpublishingconfiguration)

    def create_node(
        self,
        networkid,
        memberid,
        availabilityzone,
        instancetype,
        logpublishingconfiguration,
    ):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "CreateNode", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "CreateNode", "Member {0} not found.".format(memberid)
            )

        networkedition = self.networks.get(networkid).network_edition
        if (
            number_of_nodes_in_member(self.nodes, memberid)
            >= EDITIONS[networkedition]["MaxNodesPerMember"]
        ):
            raise ResourceLimitExceededException(
                "CreateNode",
                "Maximum number of nodes exceeded in member {0}. The maximum number of nodes you can have in a member in a {1} Edition network is {2}".format(
                    memberid,
                    networkedition,
                    EDITIONS[networkedition]["MaxNodesPerMember"],
                ),
            )

        # See if the instance family is correct
        correctinstancefamily = False
        for chkinsttypepre in EDITIONS["STANDARD"]["AllowedNodeInstanceTypes"]:
            chkinsttypepreregex = chkinsttypepre + ".*"
            if re.match(chkinsttypepreregex, instancetype, re.IGNORECASE):
                correctinstancefamily = True
                break

        if correctinstancefamily is False:
            raise InvalidRequestException(
                "CreateNode",
                "Requested instance {0} isn't supported.".format(instancetype),
            )

        # Check for specific types for starter
        if networkedition == "STARTER":
            if instancetype not in EDITIONS["STARTER"]["AllowedNodeInstanceTypes"]:
                raise InvalidRequestException(
                    "CreateNode",
                    "Instance type {0} is not supported with STARTER Edition networks.".format(
                        instancetype
                    ),
                )

        # Simple availability zone check
        chkregionpreregex = self.region_name + "[a-z]"
        if re.match(chkregionpreregex, availabilityzone, re.IGNORECASE) is None:
            raise InvalidRequestException(
                "CreateNode", "Availability Zone is not valid",
            )

        node_id = get_node_id()
        self.nodes[node_id] = ManagedBlockchainNode(
            node_id=node_id,
            networkid=networkid,
            memberid=memberid,
            availabilityzone=availabilityzone,
            instancetype=instancetype,
            logpublishingconfiguration=logpublishingconfiguration,
            region=self.region_name,
        )

        # Return the node ID
        d = {"NodeId": node_id}
        return d

    def list_nodes(self, networkid, memberid, status=None):
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "ListNodes", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "ListNodes", "Member {0} not found.".format(memberid)
            )

        # If member is deleted, cannot list nodes
        if self.members.get(memberid).member_status == "DELETED":
            raise ResourceNotFoundException(
                "ListNodes", "Member {0} not found.".format(memberid)
            )

        nodesformember = []
        for node_id in self.nodes:
            if self.nodes.get(node_id).member_id == memberid and (
                status is None or self.nodes.get(node_id).node_status == status
            ):
                nodesformember.append(self.nodes[node_id])
        return nodesformember

    def get_node(self, networkid, memberid, nodeid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "GetNode", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "GetNode", "Member {0} not found.".format(memberid)
            )

        if nodeid not in self.nodes:
            raise ResourceNotFoundException(
                "GetNode", "Node {0} not found.".format(nodeid)
            )

        # Cannot get a node than has been deleted (it does show up in the list)
        if self.nodes.get(nodeid).node_status == "DELETED":
            raise ResourceNotFoundException(
                "GetNode", "Node {0} not found.".format(nodeid)
            )

        return self.nodes.get(nodeid)

    def delete_node(self, networkid, memberid, nodeid):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "DeleteNode", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "DeleteNode", "Member {0} not found.".format(memberid)
            )

        if nodeid not in self.nodes:
            raise ResourceNotFoundException(
                "DeleteNode", "Node {0} not found.".format(nodeid)
            )

        self.nodes.get(nodeid).delete()

    def update_node(self, networkid, memberid, nodeid, logpublishingconfiguration):
        # Check if network exists
        if networkid not in self.networks:
            raise ResourceNotFoundException(
                "UpdateNode", "Network {0} not found.".format(networkid)
            )

        if memberid not in self.members:
            raise ResourceNotFoundException(
                "UpdateNode", "Member {0} not found.".format(memberid)
            )

        if nodeid not in self.nodes:
            raise ResourceNotFoundException(
                "UpdateNode", "Node {0} not found.".format(nodeid)
            )

        self.nodes.get(nodeid).update(logpublishingconfiguration)


managedblockchain_backends = BackendDict(ManagedBlockchainBackend, "managedblockchain")
