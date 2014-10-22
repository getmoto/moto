from __future__ import unicode_literals


class UnformattedGetAttTemplateException(Exception):
    description = 'Template error: resource {0} does not support attribute type {1} in Fn::GetAtt'
    status_code = 400
