from __future__ import unicode_literals
from .responses import RDS2Response

url_bases = ["https?://rds.(.+).amazonaws.com", "https?://rds.amazonaws.com"]

url_paths = {"{0}/$": RDS2Response.dispatch}
