from .responses import EC2Response


url_bases = [r"https?://ec2\.(.+)\.amazonaws\.com(|\.cn)"]

response = EC2Response()
url_paths = {"{0}/": response._dispatch}
