from __future__ import unicode_literals
from .responses import ResourceAccessManagerResponse

url_bases = ["https?://ram.(.+).amazonaws.com"]

url_paths = {
    "{0}/createresourceshare$": ResourceAccessManagerResponse.dispatch,
    "{0}/deleteresourceshare/?$": ResourceAccessManagerResponse.dispatch,
    "{0}/enablesharingwithawsorganization$": ResourceAccessManagerResponse.dispatch,
    "{0}/getresourceshares$": ResourceAccessManagerResponse.dispatch,
    "{0}/updateresourceshare$": ResourceAccessManagerResponse.dispatch,
}
