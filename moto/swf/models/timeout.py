from ..utils import now_timestamp


class Timeout(object):
    def __init__(self, obj, timestamp, kind):
        self.obj = obj
        self.timestamp = timestamp
        self.kind = kind

    @property
    def reached(self):
        return now_timestamp() >= self.timestamp
