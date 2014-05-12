from .responses import SNSResponse

url_bases = [
    "https?://sns.(.+).amazonaws.com"
]

url_paths = {
    '{0}/$': SNSResponse().dispatch,
}
