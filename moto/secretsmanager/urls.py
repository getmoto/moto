from __future__ import unicode_literals
from .responses import SecretsManagerResponse

url_bases = ["https?://secretsmanager.(.+).amazonaws.com"]

url_paths = {"{0}/$": SecretsManagerResponse.dispatch}
