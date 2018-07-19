from __future__ import unicode_literals

import email
from email.utils import parseaddr

from moto.core import BaseBackend, BaseModel
from .exceptions import MessageRejectedError
from .utils import get_random_message_id


RECIPIENT_LIMIT = 50


class Message(BaseModel):

    def __init__(self, message_id, source, subject, body, destinations):
        self.id = message_id
        self.source = source
        self.subject = subject
        self.body = body
        self.destinations = destinations


class RawMessage(BaseModel):

    def __init__(self, message_id, source, destinations, raw_data):
        self.id = message_id
        self.source = source
        self.destinations = destinations
        self.raw_data = raw_data


class SESQuota(BaseModel):

    def __init__(self, sent):
        self.sent = sent

    @property
    def sent_past_24(self):
        return self.sent


class SESBackend(BaseBackend):

    def __init__(self):
        self.addresses = []
        self.email_addresses = []
        self.domains = []
        self.sent_messages = []
        self.sent_message_count = 0

    def _is_verified_address(self, address):
        if address in self.addresses:
            return True
        user, host = address.split('@', 1)
        return host in self.domains

    def verify_email_identity(self, address):
        self.addresses.append(address)

    def verify_email_address(self, address):
        self.email_addresses.append(address)

    def verify_domain(self, domain):
        self.domains.append(domain)

    def list_identities(self):
        return self.domains + self.addresses

    def list_verified_email_addresses(self):
        return self.email_addresses

    def delete_identity(self, identity):
        if '@' in identity:
            self.addresses.remove(identity)
        else:
            self.domains.remove(identity)

    def send_email(self, source, subject, body, destinations):
        recipient_count = sum(map(len, destinations.values()))
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError('Too many recipients.')
        if not self._is_verified_address(source):
            raise MessageRejectedError(
                "Email address not verified %s" % source
            )

        message_id = get_random_message_id()
        message = Message(message_id, source, subject, body, destinations)
        self.sent_messages.append(message)
        self.sent_message_count += recipient_count
        return message

    def send_raw_email(self, source, destinations, raw_data):
        if source is not None:
            _, source_email_address = parseaddr(source)
            if source_email_address not in self.addresses:
                raise MessageRejectedError(
                    "Did not have authority to send from email %s" % source_email_address
                )

        recipient_count = len(destinations)
        message = email.message_from_string(raw_data)
        if source is None:
            if message['from'] is None:
                raise MessageRejectedError(
                    "Source not specified"
                )

            _, source_email_address = parseaddr(message['from'])
            if source_email_address not in self.addresses:
                raise MessageRejectedError(
                    "Did not have authority to send from email %s" % source_email_address
                )

        for header in 'TO', 'CC', 'BCC':
            recipient_count += sum(
                d.strip() and 1 or 0
                for d in message.get(header, '').split(',')
            )
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError('Too many recipients.')

        self.sent_message_count += recipient_count
        message_id = get_random_message_id()
        message = RawMessage(message_id, source, destinations, raw_data)
        self.sent_messages.append(message)
        return message

    def get_send_quota(self):
        return SESQuota(self.sent_message_count)


ses_backend = SESBackend()
