"""docdb-elastic base URL and path."""

from .responses import DocDBElasticResponse

url_bases = [
    r"https?://docdb-elastic\.(.+)\.amazonaws\.com",
]

# ARNs contain a slash, which arrives percent-encoded when mocking in-process
# but decoded when running in server mode, so the patterns accept both. The
# more specific patterns are listed first.
url_paths = {
    "{0}/cluster$": DocDBElasticResponse.dispatch,
    "{0}/cluster/(?P<clusterArn>.+)/start$": DocDBElasticResponse.dispatch,
    "{0}/cluster/(?P<clusterArn>.+)/stop$": DocDBElasticResponse.dispatch,
    "{0}/cluster/(?P<clusterArn>.+)$": DocDBElasticResponse.dispatch,
    "{0}/clusters$": DocDBElasticResponse.dispatch,
    "{0}/cluster-snapshot$": DocDBElasticResponse.dispatch,
    "{0}/cluster-snapshot/(?P<snapshotArn>.+)/copy$": DocDBElasticResponse.dispatch,
    "{0}/cluster-snapshot/(?P<snapshotArn>.+)/restore$": DocDBElasticResponse.dispatch,
    "{0}/cluster-snapshot/(?P<snapshotArn>.+)$": DocDBElasticResponse.dispatch,
    "{0}/cluster-snapshots$": DocDBElasticResponse.dispatch,
    "{0}/pending-action$": DocDBElasticResponse.dispatch,
    "{0}/pending-action/(?P<resourceArn>.+)$": DocDBElasticResponse.dispatch,
    "{0}/pending-actions$": DocDBElasticResponse.dispatch,
    "{0}/tags/(?P<resourceArn>.+)$": DocDBElasticResponse.dispatch,
}
