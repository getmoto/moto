from .responses import GlacierResponse

url_bases = [r"https?://glacier\.(.+)\.amazonaws.com"]

response = GlacierResponse()

url_paths = {
    "{0}/(?P<account_number>.+)/vaults$": response.all_vault_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>[^/]+)$": response.vault_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives$": response.vault_archive_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives/(?P<archive_id>.+)$": response.vault_archive_individual_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs$": response.vault_jobs_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>[^/.]+)$": response.vault_jobs_individual_response,
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>.+)/output$": response.vault_jobs_output_response,
}
