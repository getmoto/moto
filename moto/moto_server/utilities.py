import json
from flask.testing import FlaskClient

from urllib.parse import urlencode
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    # http://werkzeug.pocoo.org/docs/routing/#custom-converters

    part_isolating = False

    def __init__(self, url_map, *items):
        super().__init__(url_map)
        self.regex = items[0]


class AWSTestHelper(FlaskClient):
    def action_data(self, action_name, **kwargs):
        """
        Method calls resource with action_name and returns data of response.
        """
        opts = {"Action": action_name}
        opts.update(kwargs)
        res = self.get(
            f"/?{urlencode(opts)}",
            headers={"Host": f"{self.application.service}.us-east-1.amazonaws.com"},
        )
        return res.data.decode("utf-8")

    def action_json(self, action_name, **kwargs):
        """
        Method calls resource with action_name and returns object obtained via
        deserialization of output.
        """
        return json.loads(self.action_data(action_name, **kwargs))
