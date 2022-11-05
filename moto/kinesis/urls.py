from .responses import KinesisResponse

url_bases = [
    # Need to avoid conflicting with kinesisvideo
    r"https?://kinesis\.(.+)\.amazonaws\.com",
]

url_paths = {"{0}/$": KinesisResponse.dispatch}
