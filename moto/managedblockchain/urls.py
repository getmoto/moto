from .responses import ManagedBlockchainResponse

url_bases = [r"https?://managedblockchain\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/networks$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.network_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.networkid_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/proposals$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.proposal_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/proposals/(?P<proposalid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.proposalid_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/proposals/(?P<proposalid>[^/.]+)/votes$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.proposal_votes_response
    ),
    "{0}/invitations$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.invitation_response
    ),
    "{0}/invitations/(?P<invitationid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.invitationid_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/members$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.member_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.memberid_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.node_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes?(?P<querys>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.node_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/members/(?P<memberid>[^/.]+)/nodes/(?P<nodeid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.nodeid_response
    ),
    # >= botocore 1.19.41 (API change - memberId is now part of query-string or body)
    "{0}/networks/(?P<networkid>[^/.]+)/nodes$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.node_response
    ),
    "{0}/networks/(?P<networkid>[^/.]+)/nodes/(?P<nodeid>[^/.]+)$": ManagedBlockchainResponse.method_dispatch(
        ManagedBlockchainResponse.nodeid_response
    ),
}
