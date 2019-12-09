import json


class AWSError(Exception):
    CODE = None
    STATUS = 400

    def __init__(self, message, code=None, status=None):
        self.message = message
        self.code = code if code is not None else self.CODE
        self.status = status if status is not None else self.STATUS

    def response(self):
        return (
            json.dumps({"__type": self.code, "message": self.message}),
            dict(status=self.status),
        )


class InvalidRequestException(AWSError):
    CODE = "InvalidRequestException"


class BadSegmentException(Exception):
    def __init__(self, seg_id=None, code=None, message=None):
        self.id = seg_id
        self.code = code
        self.message = message

    def __repr__(self):
        return "<BadSegment {0}>".format("-".join([self.id, self.code, self.message]))

    def to_dict(self):
        result = {}
        if self.id is not None:
            result["Id"] = self.id
        if self.code is not None:
            result["ErrorCode"] = self.code
        if self.message is not None:
            result["Message"] = self.message

        return result
