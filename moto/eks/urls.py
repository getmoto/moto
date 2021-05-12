from __future__ import unicode_literals
from .responses import EKSResponse

url_bases = [
    "https?://eks.(.+).amazonaws.com",
]


response = EKSResponse()


url_paths = {
    "{0}/.*$": response.dispatch,
}
