from .responses import EC2Response


url_bases = [
    "https?://ec2.(.+).amazonaws.com",
]

url_paths = {
    '{0}/': EC2Response().dispatch,
}
