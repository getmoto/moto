from .responses import EmailResponse

url_bases = [
    "https?://email.us-east-1.amazonaws.com"
]

url_paths = {
    '{0}/$': EmailResponse().dispatch,
}
