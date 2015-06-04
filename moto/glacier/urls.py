from __future__ import unicode_literals
from .responses import GlacierResponse

url_bases = [
    "https?://glacier.(.+).amazonaws.com",
]

url_paths = {
    '{0}/(?P<account_number>.+)/vaults$': GlacierResponse.all_vault_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)$': GlacierResponse.vault_response,
}
