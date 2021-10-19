from .responses import RDS2Response

url_bases = [r"https?://rds\.(.+)\.amazonaws\.com", r"https?://rds\.amazonaws\.com"]

url_paths = {"{0}/$": RDS2Response.dispatch}
