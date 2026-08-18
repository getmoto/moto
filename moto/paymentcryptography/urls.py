from .responses import PaymentCryptographyControlPlaneResponse

url_bases = [r"https?://controlplane\.payment-cryptography\.(.+)\.amazonaws\.com"]
url_paths = {"{0}/$": PaymentCryptographyControlPlaneResponse.dispatch}
