from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlparse, parse_qs

from moto.core.responses import BaseResponse
from .exceptions import exception_handler
from .models import managedblockchain_backends
from .utils import (
    region_from_managedblckchain_url,
    networkid_from_managedblockchain_url,
    proposalid_from_managedblockchain_url,
    invitationid_from_managedblockchain_url,
    memberid_from_managedblockchain_request,
    nodeid_from_managedblockchain_url,
)


class ManagedBlockchainResponse(BaseResponse):
    def __init__(self, backend):
        super(ManagedBlockchainResponse, self).__init__()
        self.backend = backend

    @classmethod
    @exception_handler
    def network_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._network_response(request, full_url, headers)

    def _network_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        if method == "GET":
            return self._all_networks_response(request, full_url, headers)
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            return self._network_response_post(json_body, querystring, headers)

    def _all_networks_response(self, request, full_url, headers):
        mbcnetworks = self.backend.list_networks()
        response = json.dumps(
            {"Networks": [mbcnetwork.to_dict() for mbcnetwork in mbcnetworks]}
        )
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _network_response_post(self, json_body, querystring, headers):
        name = json_body["Name"]
        framework = json_body["Framework"]
        frameworkversion = json_body["FrameworkVersion"]
        frameworkconfiguration = json_body["FrameworkConfiguration"]
        voting_policy = json_body["VotingPolicy"]
        member_configuration = json_body["MemberConfiguration"]

        # Optional
        description = json_body.get("Description", None)

        response = self.backend.create_network(
            name,
            framework,
            frameworkversion,
            frameworkconfiguration,
            voting_policy,
            member_configuration,
            description,
        )
        return 200, headers, json.dumps(response)

    @classmethod
    @exception_handler
    def networkid_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._networkid_response(request, full_url, headers)

    def _networkid_response(self, request, full_url, headers):
        method = request.method

        if method == "GET":
            network_id = networkid_from_managedblockchain_url(full_url)
            return self._networkid_response_get(network_id, headers)

    def _networkid_response_get(self, network_id, headers):
        mbcnetwork = self.backend.get_network(network_id)
        response = json.dumps({"Network": mbcnetwork.get_format()})
        headers["content-type"] = "application/json"
        return 200, headers, response

    @classmethod
    @exception_handler
    def proposal_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._proposal_response(request, full_url, headers)

    def _proposal_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        network_id = networkid_from_managedblockchain_url(full_url)
        if method == "GET":
            return self._all_proposals_response(network_id, headers)
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            return self._proposal_response_post(
                network_id, json_body, querystring, headers
            )

    def _all_proposals_response(self, network_id, headers):
        proposals = self.backend.list_proposals(network_id)
        response = json.dumps(
            {"Proposals": [proposal.to_dict() for proposal in proposals]}
        )
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _proposal_response_post(self, network_id, json_body, querystring, headers):
        memberid = json_body["MemberId"]
        actions = json_body["Actions"]

        # Optional
        description = json_body.get("Description", None)

        response = self.backend.create_proposal(
            network_id, memberid, actions, description,
        )
        return 200, headers, json.dumps(response)

    @classmethod
    @exception_handler
    def proposalid_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._proposalid_response(request, full_url, headers)

    def _proposalid_response(self, request, full_url, headers):
        method = request.method
        network_id = networkid_from_managedblockchain_url(full_url)
        if method == "GET":
            proposal_id = proposalid_from_managedblockchain_url(full_url)
            return self._proposalid_response_get(network_id, proposal_id, headers)

    def _proposalid_response_get(self, network_id, proposal_id, headers):
        proposal = self.backend.get_proposal(network_id, proposal_id)
        response = json.dumps({"Proposal": proposal.get_format()})
        headers["content-type"] = "application/json"
        return 200, headers, response

    @classmethod
    @exception_handler
    def proposal_votes_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._proposal_votes_response(request, full_url, headers)

    def _proposal_votes_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        network_id = networkid_from_managedblockchain_url(full_url)
        proposal_id = proposalid_from_managedblockchain_url(full_url)
        if method == "GET":
            return self._all_proposal_votes_response(network_id, proposal_id, headers)
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            return self._proposal_votes_response_post(
                network_id, proposal_id, json_body, querystring, headers
            )

    def _all_proposal_votes_response(self, network_id, proposal_id, headers):
        proposalvotes = self.backend.list_proposal_votes(network_id, proposal_id)
        response = json.dumps({"ProposalVotes": proposalvotes})
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _proposal_votes_response_post(
        self, network_id, proposal_id, json_body, querystring, headers
    ):
        votermemberid = json_body["VoterMemberId"]
        vote = json_body["Vote"]

        self.backend.vote_on_proposal(
            network_id, proposal_id, votermemberid, vote,
        )
        return 200, headers, ""

    @classmethod
    @exception_handler
    def invitation_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._invitation_response(request, full_url, headers)

    def _invitation_response(self, request, full_url, headers):
        method = request.method
        if method == "GET":
            return self._all_invitation_response(request, full_url, headers)

    def _all_invitation_response(self, request, full_url, headers):
        invitations = self.backend.list_invitations()
        response = json.dumps(
            {"Invitations": [invitation.to_dict() for invitation in invitations]}
        )
        headers["content-type"] = "application/json"
        return 200, headers, response

    @classmethod
    @exception_handler
    def invitationid_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._invitationid_response(request, full_url, headers)

    def _invitationid_response(self, request, full_url, headers):
        method = request.method
        if method == "DELETE":
            invitation_id = invitationid_from_managedblockchain_url(full_url)
            return self._invitationid_response_delete(invitation_id, headers)

    def _invitationid_response_delete(self, invitation_id, headers):
        self.backend.reject_invitation(invitation_id)
        headers["content-type"] = "application/json"
        return 200, headers, ""

    @classmethod
    @exception_handler
    def member_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._member_response(request, full_url, headers)

    def _member_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        network_id = networkid_from_managedblockchain_url(full_url)
        if method == "GET":
            return self._all_members_response(network_id, headers)
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            return self._member_response_post(
                network_id, json_body, querystring, headers
            )

    def _all_members_response(self, network_id, headers):
        members = self.backend.list_members(network_id)
        response = json.dumps({"Members": [member.to_dict() for member in members]})
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _member_response_post(self, network_id, json_body, querystring, headers):
        invitationid = json_body["InvitationId"]
        member_configuration = json_body["MemberConfiguration"]

        response = self.backend.create_member(
            invitationid, network_id, member_configuration,
        )
        return 200, headers, json.dumps(response)

    @classmethod
    @exception_handler
    def memberid_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._memberid_response(request, full_url, headers)

    def _memberid_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        network_id = networkid_from_managedblockchain_url(full_url)
        member_id = memberid_from_managedblockchain_request(full_url, body)
        if method == "GET":
            return self._memberid_response_get(network_id, member_id, headers)
        elif method == "PATCH":
            json_body = json.loads(body.decode("utf-8"))
            return self._memberid_response_patch(
                network_id, member_id, json_body, headers
            )
        elif method == "DELETE":
            return self._memberid_response_delete(network_id, member_id, headers)

    def _memberid_response_get(self, network_id, member_id, headers):
        member = self.backend.get_member(network_id, member_id)
        response = json.dumps({"Member": member.get_format()})
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _memberid_response_patch(self, network_id, member_id, json_body, headers):
        logpublishingconfiguration = json_body["LogPublishingConfiguration"]
        self.backend.update_member(
            network_id, member_id, logpublishingconfiguration,
        )
        return 200, headers, ""

    def _memberid_response_delete(self, network_id, member_id, headers):
        self.backend.delete_member(network_id, member_id)
        headers["content-type"] = "application/json"
        return 200, headers, ""

    @classmethod
    @exception_handler
    def node_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._node_response(request, full_url, headers)

    def _node_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        network_id = networkid_from_managedblockchain_url(full_url)
        member_id = memberid_from_managedblockchain_request(full_url, body)
        if method == "GET":
            status = None
            if "status" in querystring:
                status = querystring["status"][0]
            return self._all_nodes_response(network_id, member_id, status, headers)
        elif method == "POST":
            json_body = json.loads(body.decode("utf-8"))
            return self._node_response_post(
                network_id, member_id, json_body, querystring, headers
            )

    def _all_nodes_response(self, network_id, member_id, status, headers):
        nodes = self.backend.list_nodes(network_id, member_id, status)
        response = json.dumps({"Nodes": [node.to_dict() for node in nodes]})
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _node_response_post(
        self, network_id, member_id, json_body, querystring, headers
    ):
        instancetype = json_body["NodeConfiguration"]["InstanceType"]
        availabilityzone = json_body["NodeConfiguration"]["AvailabilityZone"]
        logpublishingconfiguration = json_body["NodeConfiguration"][
            "LogPublishingConfiguration"
        ]

        response = self.backend.create_node(
            network_id,
            member_id,
            availabilityzone,
            instancetype,
            logpublishingconfiguration,
        )
        return 200, headers, json.dumps(response)

    @classmethod
    @exception_handler
    def nodeid_response(clazz, request, full_url, headers):
        region_name = region_from_managedblckchain_url(full_url)
        response_instance = ManagedBlockchainResponse(
            managedblockchain_backends[region_name]
        )
        return response_instance._nodeid_response(request, full_url, headers)

    def _nodeid_response(self, request, full_url, headers):
        method = request.method
        if hasattr(request, "body"):
            body = request.body
        else:
            body = request.data
        network_id = networkid_from_managedblockchain_url(full_url)
        member_id = memberid_from_managedblockchain_request(full_url, body)
        node_id = nodeid_from_managedblockchain_url(full_url)
        if method == "GET":
            return self._nodeid_response_get(network_id, member_id, node_id, headers)
        elif method == "PATCH":
            json_body = json.loads(body.decode("utf-8"))
            return self._nodeid_response_patch(
                network_id, member_id, node_id, json_body, headers
            )
        elif method == "DELETE":
            return self._nodeid_response_delete(network_id, member_id, node_id, headers)

    def _nodeid_response_get(self, network_id, member_id, node_id, headers):
        node = self.backend.get_node(network_id, member_id, node_id)
        response = json.dumps({"Node": node.get_format()})
        headers["content-type"] = "application/json"
        return 200, headers, response

    def _nodeid_response_patch(
        self, network_id, member_id, node_id, json_body, headers
    ):
        logpublishingconfiguration = json_body
        self.backend.update_node(
            network_id, member_id, node_id, logpublishingconfiguration,
        )
        return 200, headers, ""

    def _nodeid_response_delete(self, network_id, member_id, node_id, headers):
        self.backend.delete_node(network_id, member_id, node_id)
        headers["content-type"] = "application/json"
        return 200, headers, ""
