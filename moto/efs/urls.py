from __future__ import unicode_literals
from .responses import EFSResponse

url_bases = [
    "https?://elasticfilesystem.(.+).amazonaws.com",
]


response = EFSResponse()


url_paths = {
    "{0}/.*$": response.dispatch,
}
