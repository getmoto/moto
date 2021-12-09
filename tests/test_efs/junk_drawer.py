def has_status_code(response, code):
    return response["ResponseMetadata"]["HTTPStatusCode"] == code
