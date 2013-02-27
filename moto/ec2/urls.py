from .responses import EC2Response

urls = {
    "https?://ec2.us-east-1.amazonaws.com/": EC2Response().dispatch,
}
