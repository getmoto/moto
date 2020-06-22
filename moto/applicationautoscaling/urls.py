from __future__ import unicode_literals
from .responses import ApplicationAutoScalingResponse

url_bases = ["https?://application-autoscaling.(.+).amazonaws.com"]

url_paths = {
    "{0}/$": ApplicationAutoScalingResponse.dispatch,
}
