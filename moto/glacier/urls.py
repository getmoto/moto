from __future__ import unicode_literals
from .responses import GlacierResponse

url_bases = [
    "https?://glacier.(.+).amazonaws.com",
]

url_paths = {
    '{0}/(?P<account_number>.+)/vaults$': GlacierResponse.all_vault_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>[^/.]+)$': GlacierResponse.vault_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives$': GlacierResponse.vault_archive_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives/(?P<archive_id>.+)$': GlacierResponse.vault_archive_individual_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs$': GlacierResponse.vault_jobs_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>[^/.]+)$': GlacierResponse.vault_jobs_individual_response,
    '{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>.+)/output$': GlacierResponse.vault_jobs_output_response,
}
