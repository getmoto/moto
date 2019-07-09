from __future__ import unicode_literals

import email
from email.utils import parseaddr

from moto.core import BaseBackend, BaseModel
from moto.sns.models import sns_backends
from .exceptions import MessageRejectedError
from .utils import get_random_message_id
from .feedback import COMMON_MAIL, BOUNCE, COMPLAINT, DELIVERY

RECIPIENT_LIMIT = 50


class SESFeedback(BaseModel):

    BOUNCE = "Bounce"
    COMPLAINT = "Complaint"
    DELIVERY = "Delivery"

    SUCCESS_ADDR = "success"
    BOUNCE_ADDR = "bounce"
    COMPLAINT_ADDR = "complaint"

    FEEDBACK_SUCCESS_MSG = {"test": "success"}
    FEEDBACK_BOUNCE_MSG = {"test": "bounce"}
    FEEDBACK_COMPLAINT_MSG = {"test": "complaint"}

    @staticmethod
    def generate_message(msg_type):
        msg = dict(COMMON_MAIL)
        if msg_type == SESFeedback.BOUNCE:
            msg["bounce"] = BOUNCE
        elif msg_type == SESFeedback.COMPLAINT:
            msg["complaint"] = COMPLAINT
        elif msg_type == SESFeedback.DELIVERY:
            msg["delivery"] = DELIVERY

        return msg


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
        self.sns_topics = {}

    def _is_verified_address(self, source):
        _, address = parseaddr(source)
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

    def send_email(self, source, subject, body, destinations, region):
        recipient_count = sum(map(len, destinations.values()))
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError('Too many recipients.')
        if not self._is_verified_address(source):
            raise MessageRejectedError(
                "Email address not verified %s" % source
            )

        self.__process_sns_feedback__(source, destinations, region)

        message_id = get_random_message_id()
        message = Message(message_id, source, subject, body, destinations)
        self.sent_messages.append(message)
        self.sent_message_count += recipient_count
        return message

    def __type_of_message__(self, destinations):
        """Checks the destination for any special address that could indicate delivery, complaint or bounce
        like in SES simualtor"""
        alladdress = destinations.get("ToAddresses", []) + destinations.get("CcAddresses", []) + destinations.get("BccAddresses", [])
        for addr in alladdress:
            if SESFeedback.SUCCESS_ADDR in addr:
                return SESFeedback.DELIVERY
            elif SESFeedback.COMPLAINT_ADDR in addr:
                return SESFeedback.COMPLAINT
            elif SESFeedback.BOUNCE_ADDR in addr:
                return SESFeedback.BOUNCE

        return None

    def __generate_feedback__(self, msg_type):
        """Generates the SNS message for the feedback"""
        return SESFeedback.generate_message(msg_type)

    def __process_sns_feedback__(self, source, destinations, region):
        domain = str(source)
        if "@" in domain:
            domain = domain.split("@")[1]
        if domain in self.sns_topics:
            msg_type = self.__type_of_message__(destinations)
            if msg_type is not None:
                sns_topic = self.sns_topics[domain].get(msg_type, None)
                if sns_topic is not None:
                    message = self.__generate_feedback__(msg_type)
                    if message:
                        sns_backends[region].publish(sns_topic, message)

    def send_raw_email(self, source, destinations, raw_data, region):
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

        self.__process_sns_feedback__(source, destinations, region)

        self.sent_message_count += recipient_count
        message_id = get_random_message_id()
        message = RawMessage(message_id, source, destinations, raw_data)
        self.sent_messages.append(message)
        return message

    def get_send_quota(self):
        return SESQuota(self.sent_message_count)

    def set_identity_notification_topic(self, identity, notification_type, sns_topic):
        identity_sns_topics = self.sns_topics.get(identity, {})
        if sns_topic is None:
            del identity_sns_topics[notification_type]
        else:
            identity_sns_topics[notification_type] = sns_topic

        self.sns_topics[identity] = identity_sns_topics

        return {}


ses_backend = SESBackend()
