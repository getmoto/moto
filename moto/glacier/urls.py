from .responses import GlacierResponse

url_bases = [r"https?://glacier\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/(?P<account_number>.+)/vaults$": GlacierResponse.method_dispatch(
        GlacierResponse.all_vault_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>[^/]+)$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_archive_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/archives/(?P<archive_id>.+)$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_archive_individual_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_jobs_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>[^/.]+)$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_jobs_individual_response
    ),
    "{0}/(?P<account_number>.+)/vaults/(?P<vault_name>.+)/jobs/(?P<job_id>.+)/output$": GlacierResponse.method_dispatch(
        GlacierResponse.vault_jobs_output_response
    ),
}
