"""vpclattice base URL and path."""

from .responses import VPCLatticeResponse

url_bases = [
    r"https?://vpc-lattice\.(.+)\.amazonaws\.com",
]

url_paths = {
    "{0}/accesslogsubscriptions$": VPCLatticeResponse.dispatch,
    "{0}/accesslogsubscriptions/(?P<accessLogSubscriptionIdentifier>.+)$": VPCLatticeResponse.dispatch,
    "{0}/services$": VPCLatticeResponse.dispatch,
    "{0}/servicenetworks$": VPCLatticeResponse.dispatch,
    "{0}/servicenetworkvpcassociations$": VPCLatticeResponse.dispatch,
    "{0}/services/(?P<serviceIdentifier>[^/]+)/listeners/(?P<listenerIdentifier>[^/]+)/rules$": VPCLatticeResponse.dispatch,
    "{0}/tags/(?P<resourceArn>[^/]+)$": VPCLatticeResponse.dispatch,
}
