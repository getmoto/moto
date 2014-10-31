from __future__ import unicode_literals
from boto.exception import BotoServerError
from jinja2 import Template



class UnformattedGetAttTemplateException(Exception):
    description = 'Template error: resource {0} does not support attribute type {1} in Fn::GetAtt'
    status_code = 400


class ValidationError(BotoServerError):
    def __init__(self, name_or_id):
        template = Template(STACK_DOES_NOT_EXIST_RESPONSE)
        super(ValidationError, self).__init__(status=400, reason='Bad Request',
                                              body=template.render(name_or_id=name_or_id))

STACK_DOES_NOT_EXIST_RESPONSE = """<ErrorResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <Error>
    <Type>Sender</Type>
    <Code>ValidationError</Code>
    <Message>Stack:{{ name_or_id }} does not exist</Message>
  </Error>
  <RequestId>cf4c737e-5ae2-11e4-a7c9-ad44eEXAMPLE</RequestId>
</ErrorResponse>
"""
