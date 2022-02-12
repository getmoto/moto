from .responses import ElasticsearchServiceResponse

url_bases = [
    r"https?://es\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/2015-01-01/domain$": ElasticsearchServiceResponse.list_domains,
    "{0}/2015-01-01/es/domain$": ElasticsearchServiceResponse.domains,
    "{0}/2015-01-01/es/domain/(?P<domainname>[^/]+)": ElasticsearchServiceResponse.domain,
}
