from __future__ import unicode_literals
from .responses import DatabaseMigrationServiceResponse

url_bases = [
    "https?://dms.(.+).amazonaws.com",
]


url_paths = {
    "{0}/$": DatabaseMigrationServiceResponse.dispatch,
}
