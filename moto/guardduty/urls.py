from __future__ import unicode_literals
from .responses import GuardDutyResponse

response = GuardDutyResponse()

url_bases = [
    "https?://guardduty\\.(.+)\\.amazonaws\\.com",
]


url_paths = {
    "{0}/detector$": response.detector,
}
