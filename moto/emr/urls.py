from .responses import ElasticMapReduceResponse

url_bases = [
    "https?://elasticmapreduce.(.+).amazonaws.com",
]

url_paths = {
    '{0}/$': ElasticMapReduceResponse().dispatch,
}
