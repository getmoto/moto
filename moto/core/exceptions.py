from werkzeug.exceptions import HTTPException
from jinja2 import DictLoader, Environment


ERROR_RESPONSE = u"""<?xml version="1.0" encoding="UTF-8"?>
  <Response>
    <Errors>
      <Error>
        <Code>{{code}}</Code>
        <Message>{{message}}</Message>
        {% block extra %}{% endblock %}
      </Error>
    </Errors>
  <RequestID>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestID>
</Response>
"""


class RESTError(HTTPException):
    templates = {
        'error': ERROR_RESPONSE
    }

    def __init__(self, code, message, template='error', **kwargs):
        super(RESTError, self).__init__()
        env = Environment(loader=DictLoader(self.templates))
        self.description = env.get_template(template).render(
            code=code, message=message, **kwargs)
