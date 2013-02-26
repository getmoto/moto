from moto.core import BaseBackend
from .utils import get_random_message_id


class Message(object):
    def __init__(self, message_id, source, subject, body, destination):
        self.id = message_id
        self.source = source
        self.subject = subject
        self.body = body
        self.destination = destination


class RawMessage(object):
    def __init__(self, message_id, source, destination, raw_data):
        self.id = message_id
        self.source = source
        self.destination = destination
        self.raw_data = raw_data


class SESQuota(object):
    def __init__(self, messages):
        self.messages = messages

    @property
    def sent_past_24(self):
        return len(self.messages)


class SESBackend(BaseBackend):
    def __init__(self):
        self.addresses = []
        self.sent_messages = []

    def verify_email_identity(self, address):
        self.addresses.append(address)

    def verify_domain(self, domain):
        self.addresses.append(domain)

    def list_identities(self):
        return self.addresses

    def delete_identity(self, identity):
        self.addresses.remove(identity)

    def send_email(self, source, subject, body, destination):
        if source not in self.addresses:
            return False

        message_id = get_random_message_id()
        message = Message(message_id, source, subject, body, destination)
        self.sent_messages.append(message)
        return message

    def send_raw_email(self, source, destination, raw_data):
        if source not in self.addresses:
            return False

        message_id = get_random_message_id()
        message = RawMessage(message_id, source, destination, raw_data)
        self.sent_messages.append(message)
        return message

    def get_send_quota(self):
        return SESQuota(self.sent_messages)

ses_backend = SESBackend()
