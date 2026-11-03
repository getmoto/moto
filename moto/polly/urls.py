from .responses import PollyResponse

url_bases = [r"https?://polly\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/.*$": PollyResponse.dispatch,
}
