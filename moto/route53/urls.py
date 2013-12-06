import responses

url_bases = [
    "https://route53.amazonaws.com/201.-..-../hostedzone",
]

url_paths = {
    '{0}$': responses.list_or_create_hostzone_response,
    '{0}/.+$': responses.get_or_delete_hostzone_response,
    '{0}/.+/rrset$': responses.rrset_response,
}
