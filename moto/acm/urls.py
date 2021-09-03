from .responses import AWSCertificateManagerResponse

url_bases = ["https?://acm\.(.+)\.amazonaws\.com"]

url_paths = {"{0}/$": AWSCertificateManagerResponse.dispatch}
