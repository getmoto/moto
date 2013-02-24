from moto.core import BaseBackend
from moto.core.utils import camelcase_to_underscores


class Queue(object):
    camelcase_attributes = ['VisibilityTimeout']

    def __init__(self, name, visibility_timeout):
        self.name = name
        self.visibility_timeout = visibility_timeout

    @property
    def attributes(self):
        result = {}
        for attribute in self.camelcase_attributes:
            result[attribute] = getattr(self, camelcase_to_underscores(attribute))
        return result

class SQSBackend(BaseBackend):

    def __init__(self):
        self.queues = {}
        super(SQSBackend, self).__init__()

    def create_queue(self, name, visibility_timeout):
        queue = Queue(name, visibility_timeout)
        self.queues[name] = queue
        return queue

    def list_queues(self):
        return self.queues.values()

    def get_queue(self, queue_name):
        return self.queues[queue_name]

    def delete_queue(self, queue_name):
        if queue_name in self.queues:
            return self.queues.pop(queue_name)
        return False

    def set_queue_attribute(self, queue_name, key, value):
        queue = self.get_queue(queue_name)
        setattr(queue, key, value)
        return queue

sqs_backend = SQSBackend()
