from .responses import EmailResponse

base_url = "https://email.us-east-1.amazonaws.com"

urls = {
    '{0}/$'.format(base_url): EmailResponse().dispatch,
}
