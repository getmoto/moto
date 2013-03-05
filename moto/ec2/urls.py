from .responses import EC2Response


url_bases = [
    "https?://ec2.us-east-1.amazonaws.com",
]

url_paths = {
    '{0}/': EC2Response().dispatch,
}
