from __future__ import unicode_literals
from .responses import ElastictranscoderResponse


url_bases = [
    "https?://elastictranscoder.(.+).amazonaws.com",
]

response = ElastictranscoderResponse()

url_paths = {
    '{0}/2012-09-25/presets': response.create_preset,
    '{0}/2012-09-25/presets/(?P<job_id>.+)': response.delete_preset,
    '{0}/2012-09-25/jobs': response.create_job,
    '{0}/2012-09-25/jobs/(?P<preset_id>.+)': response.check_job
}
