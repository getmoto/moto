import datetime
import json
from urllib.parse import urlparse

from moto.core.responses import BaseResponse


class InstanceMetadataResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name=None)

    def backends(self):
        pass

    def metadata_response(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        """
        Mock response for localhost metadata

        http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AESDG-chapter-instancedata.html
        """

        parsed_url = urlparse(full_url)
        tomorrow = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        credentials = dict(
            AccessKeyId="test-key",
            SecretAccessKey="test-secret-key",
            Token="test-session-token",
            Expiration=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        path = parsed_url.path

        meta_data_prefix = "/latest/meta-data/"
        # Strip prefix if it is there
        if path.startswith(meta_data_prefix):
            path = path[len(meta_data_prefix) :]

        if path == "":
            result = "iam"
        elif path == "iam":
            result = json.dumps({"security-credentials": {"default-role": credentials}})
        elif path == "iam/security-credentials/":
            result = "default-role"
        elif path == "iam/security-credentials/default-role":
            result = json.dumps(credentials)
        else:
            raise NotImplementedError(
                "The {0} metadata path has not been implemented".format(path)
            )
        return 200, headers, result
