from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlparse, parse_qs

from moto.core.responses import BaseResponse
from .models import managedblockchain_backends
from .utils import (
    region_from_managedblckchain_url,
    networkid_from_managedblockchain_url,
    proposalid_from_managedblockchain_url,
)


class ManagedBlockchainResponse(BaseResponse):
    def __init__(self, backend):
        super(ManagedBlockchainResponse, self).__init__()
        self.backend = backend

    @classmethod
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
            return self._proposal_response_post(network_id, json_body, querystring, headers)

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
