from __future__ import unicode_literals, division

import datetime
import re

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from .exceptions import (
    BadRequestException,
    ResourceNotFoundException,
    InvalidRequestException,
    ResourceLimitExceededException,
)

from .utils import (
    get_network_id,
    get_member_id,
    get_proposal_id,
    get_invitation_id,
    member_name_exist_in_network,
    number_of_members_in_network,
    admin_password_ok,
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
        if datetime.datetime.utcnow() > self.expirtationdate:
            self.status = "EXPIRED"
            return False

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

        return True


class ManagedBlockchainInvitation(BaseModel):
    def __init__(
        self,
        id,
        networkid,
        networkname,
        networkframework,
        networkframeworkversion,
        networkcreationdate,
        region,
        networkdescription=None,
    ):
        self.id = id
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
        self, id, networkid, member_configuration, region,
    ):
        self.creationdate = datetime.datetime.utcnow()
        self.id = id
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


class ManagedBlockchainBackend(BaseBackend):
    def __init__(self, region_name):
        self.networks = {}
        self.members = {}
        self.proposals = {}
        self.invitations = {}
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

        ## Generate proposal ID
        proposal_id = get_proposal_id()

        self.proposals[proposal_id] = ManagedBlockchainProposal(
            id=proposal_id,
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

        # Check to see if this member already voted
        # TODO Verify exception
        if votermemberid in self.proposals.get(proposalid).proposal_votes:
            raise BadRequestException("VoteOnProposal", "Invalid request body")

        # Will return false if vote was not cast (e.g., status wrong)
        if self.proposals.get(proposalid).set_vote(
            votermemberid, self.members.get(votermemberid).name, vote.upper()
        ):
            if self.proposals.get(proposalid).proposal_status == "APPROVED":
                ## Generate invitations
                for propinvitation in self.proposals.get(proposalid).proposal_actions(
                    "Invitations"
                ):
                    invitation_id = get_invitation_id()
                    self.invitations[invitation_id] = ManagedBlockchainInvitation(
                        id=invitation_id,
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
                        networkdescription=self.networks.get(
                            networkid
                        ).network_description,
                    )

                ## Delete members
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
            id=member_id,
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

        ## Cannot get a member than has been delted (it does show up in the list)
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


managedblockchain_backends = {}
for region in Session().get_available_regions("managedblockchain"):
    managedblockchain_backends[region] = ManagedBlockchainBackend(region)
