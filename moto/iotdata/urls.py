from __future__ import unicode_literals
from .responses import IoTDataPlaneResponse

url_bases = ["https?://data.iot.(.+).amazonaws.com"]


response = IoTDataPlaneResponse()


url_paths = {
    #
    # Paths for :class:`moto.core.models.MockAWS`
    #
    # This route requires special handling.
    "{0}/topics/(?P<topic>.*)$": response.dispatch_publish,
    # The remaining routes can be handled by the default dispatcher.
    "{0}/.*$": response.dispatch,
    #
    # (Flask) Paths for :class:`moto.core.models.ServerModeMockAWS`
    #
    # This route requires special handling.
    "{0}/topics/<path:topic>$": response.dispatch_publish,
    # The remaining routes can be handled by the default dispatcher.
    "{0}/<path:route>$": response.dispatch,
}
