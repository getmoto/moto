from __future__ import unicode_literals
from .responses import IoTResponse

url_bases = ["https?://iot.(.+).amazonaws.com"]


response = IoTResponse()


url_paths = {"{0}/.*$": response.dispatch}
