from __future__ import unicode_literals
from .responses import ManagedBlockchainResponse

url_bases = ["https?://managedblockchain.(.+).amazonaws.com"]

url_paths = {
    "{0}/networks$": ManagedBlockchainResponse.network_response,
    "{0}/networks/(?P<networkid>[^/.]+)$": ManagedBlockchainResponse.networkid_response,
    "{0}/networks/(?P<networkid>[^/.]+)/proposals$": ManagedBlockchainResponse.proposal_response,
    "{0}/networks/(?P<networkid>[^/.]+)/proposals/(?P<proposalid>[^/.]+)$": ManagedBlockchainResponse.proposalid_response,
}
