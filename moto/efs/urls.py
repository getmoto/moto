from __future__ import unicode_literals

from .responses import EFSResponse

url_bases = [
    r"https?://elasticfilesystem\.(.+)\.amazonaws.com",
    r"https?://elasticfilesystem\.amazonaws.com",
]


response = EFSResponse()


url_paths = {
    "{0}/.*?$": response.dispatch,
    "/2015-02-01/file-systems": response.dispatch,
    "/2015-02-01/file-systems/<file_system_id>": response.dispatch,
    "/2015-02-01/file-systems/<file_system_id>/backup-policy": response.dispatch,
    "/2015-02-01/mount-targets": response.dispatch,
    "/2015-02-01/mount-targets/<mount_target_id>": response.dispatch,
}
