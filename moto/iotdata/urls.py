from __future__ import unicode_literals
from .responses import IoTDataPlaneResponse

url_bases = ["https?://data.iot.(.+).amazonaws.com"]


response = IoTDataPlaneResponse()


url_paths = {"{0}/.*$": response.dispatch}
