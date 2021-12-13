from __future__ import unicode_literals

from moto.rds3.responses import RDSResponse

url_bases = [
    "https?://rds.(.+).amazonaws.com(|.cn)",
    "https?://rds.amazonaws.com",
]

url_paths = {
    "{0}/$": RDSResponse.dispatch,
}
