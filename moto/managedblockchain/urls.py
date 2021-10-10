from __future__ import unicode_literals
from .responses import ManagedBlockchainResponse

url_bases = [r"https?://managedblockchain\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/networks$": ManagedBlockchainResponse.network_response,
    "{0}/networks/(?P<networkid>[^/.]+)$": ManagedBlockchainResponse.networkid_response,
    "{0}/networks/(?P<networkid>[^/.]+)/proposals$": ManagedBlockchainResponse.proposal_response,
    "{0}/networks/(?P<networkid>[^/.]+)/proposals/(?P<proposalid>[^/.]+)$": ManagedBlockchainResponse.proposalid_response,
    "{0}/networks/(?P<networkid>[^/.]+)/proposals/(?P<proposalid>[^/.]+)/votes$": ManagedBlockchainResponse.proposal_votes_response,
    "{0}/invitations$": ManagedBlockchainResponse.invitation_response,
    "{0}/invitations/(?P<invitationid>[^/.]+)$": ManagedBlockchainResponse.invitationid_response,
    "{0}/networks/(?P<networkid>[^/.]+)/members$": ManagedBlockchainResponse.member_response,
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)$": ManagedBlockchainResponse.memberid_response,
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes$": ManagedBlockchainResponse.node_response,
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes?(?P<querys>[^/.]+)$": ManagedBlockchainResponse.node_response,
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes/(?P<nodeid>[^/.]+)$": ManagedBlockchainResponse.nodeid_response,
    # >= botocore 1.19.41 (API change - memberId is now part of query-string or body)
    "{0}/networks/(?P<networkid>[^/.]+)/nodes$": ManagedBlockchainResponse.node_response,
    "{0}/networks/(?P<networkid>[^/.]+)/nodes/(?P<nodeid>[^/.]+)$": ManagedBlockchainResponse.nodeid_response,
}
