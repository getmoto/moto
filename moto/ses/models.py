from __future__ import unicode_literals

import re
import json
import email
import datetime
from email.mime.base import MIMEBase
from email.utils import parseaddr
from email.mime.multipart import MIMEMultipart
from email.encoders import encode_7or8bit

from moto.core import BaseBackend, BaseModel
from moto.sns.models import sns_backends
from .exceptions import (
    MessageRejectedError,
    ConfigurationSetDoesNotExist,
    EventDestinationAlreadyExists,
    TemplateNameAlreadyExists,
    ValidationError,
    InvalidParameterValue,
    InvalidRenderingParameterException,
    TemplateDoesNotExist,
    RuleSetNameAlreadyExists,
    RuleSetDoesNotExist,
    RuleAlreadyExists,
    MissingRenderingAttributeException,
)
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


class TemplateMessage(BaseModel):
    def __init__(self, message_id, source, template, template_data, destinations):
        self.id = message_id
        self.source = source
        self.template = template
        self.template_data = template_data
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


def are_all_variables_present(template, template_data):
    subject_part = template["subject_part"]
    text_part = template["text_part"]
    html_part = template["html_part"]

    for var in re.findall("{{(.+?)}}", subject_part + text_part + html_part):
        if not template_data.get(var):
            return var, False
    return None, True


class SESBackend(BaseBackend):
    def __init__(self):
        self.addresses = []
        self.email_addresses = []
        self.domains = []
        self.sent_messages = []
        self.sent_message_count = 0
        self.rejected_messages_count = 0
        self.sns_topics = {}
        self.config_set = {}
        self.config_set_event_destination = {}
        self.event_destinations = {}
        self.templates = {}
        self.receipt_rule_set = {}

    def _is_verified_address(self, source):
        _, address = parseaddr(source)
        if address in self.addresses:
            return True
        if address in self.email_addresses:
            return True
        user, host = address.split("@", 1)
        return host in self.domains

    def verify_email_identity(self, address):
        _, address = parseaddr(address)
        self.addresses.append(address)

    def verify_email_address(self, address):
        _, address = parseaddr(address)
        self.email_addresses.append(address)

    def verify_domain(self, domain):
        if domain.lower() not in self.domains:
            self.domains.append(domain.lower())

    def list_identities(self):
        return self.domains + self.addresses

    def list_verified_email_addresses(self):
        return self.email_addresses

    def delete_identity(self, identity):
        if "@" in identity:
            self.addresses.remove(identity)
        else:
            self.domains.remove(identity)

    def send_email(self, source, subject, body, destinations, region):
        recipient_count = sum(map(len, destinations.values()))
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError("Too many recipients.")
        if not self._is_verified_address(source):
            self.rejected_messages_count += 1
            raise MessageRejectedError("Email address not verified %s" % source)

        self.__process_sns_feedback__(source, destinations, region)

        message_id = get_random_message_id()
        message = Message(message_id, source, subject, body, destinations)
        self.sent_messages.append(message)
        self.sent_message_count += recipient_count
        return message

    def send_templated_email(
        self, source, template, template_data, destinations, region
    ):
        recipient_count = sum(map(len, destinations.values()))
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError("Too many recipients.")
        if not self._is_verified_address(source):
            self.rejected_messages_count += 1
            raise MessageRejectedError("Email address not verified %s" % source)

        if not self.templates.get(template[0]):
            raise TemplateDoesNotExist("Template (%s) does not exist" % template[0])

        self.__process_sns_feedback__(source, destinations, region)

        message_id = get_random_message_id()
        message = TemplateMessage(
            message_id, source, template, template_data, destinations
        )
        self.sent_messages.append(message)
        self.sent_message_count += recipient_count
        return message

    def __type_of_message__(self, destinations):
        """Checks the destination for any special address that could indicate delivery,
        complaint or bounce like in SES simulator"""
        if isinstance(destinations, list):
            alladdress = destinations
        else:
            alladdress = (
                destinations.get("ToAddresses", [])
                + destinations.get("CcAddresses", [])
                + destinations.get("BccAddresses", [])
            )

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
                        sns_backends[region].publish(message, arn=sns_topic)

    def send_raw_email(self, source, destinations, raw_data, region):
        if source is not None:
            _, source_email_address = parseaddr(source)
            if not self._is_verified_address(source_email_address):
                raise MessageRejectedError(
                    "Did not have authority to send from email %s"
                    % source_email_address
                )

        recipient_count = len(destinations)
        message = email.message_from_string(raw_data)
        if source is None:
            if message["from"] is None:
                raise MessageRejectedError("Source not specified")

            _, source_email_address = parseaddr(message["from"])
            if not self._is_verified_address(source_email_address):
                raise MessageRejectedError(
                    "Did not have authority to send from email %s"
                    % source_email_address
                )

        for header in "TO", "CC", "BCC":
            recipient_count += sum(
                d.strip() and 1 or 0 for d in message.get(header, "").split(",")
            )
        if recipient_count > RECIPIENT_LIMIT:
            raise MessageRejectedError("Too many recipients.")

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

    def create_configuration_set(self, configuration_set_name):
        self.config_set[configuration_set_name] = 1
        return {}

    def create_configuration_set_event_destination(
        self, configuration_set_name, event_destination
    ):

        if self.config_set.get(configuration_set_name) is None:
            raise ConfigurationSetDoesNotExist("Invalid Configuration Set Name.")

        if self.event_destinations.get(event_destination["Name"]):
            raise EventDestinationAlreadyExists("Duplicate Event destination Name.")

        self.config_set_event_destination[configuration_set_name] = event_destination
        self.event_destinations[event_destination["Name"]] = 1

        return {}

    def get_send_statistics(self):

        statistics = {}
        statistics["DeliveryAttempts"] = self.sent_message_count
        statistics["Rejects"] = self.rejected_messages_count
        statistics["Complaints"] = 0
        statistics["Bounces"] = 0
        statistics["Timestamp"] = datetime.datetime.utcnow()
        return statistics

    def add_template(self, template_info):
        template_name = template_info["template_name"]
        if not template_name:
            raise ValidationError(
                "1 validation error detected: "
                "Value null at 'template.templateName'"
                "failed to satisfy constraint: Member must not be null"
            )

        if self.templates.get(template_name, None):
            raise TemplateNameAlreadyExists("Duplicate Template Name.")

        template_subject = template_info["subject_part"]
        if not template_subject:
            raise InvalidParameterValue("The subject must be specified.")
        self.templates[template_name] = template_info

    def update_template(self, template_info):
        template_name = template_info["template_name"]
        if not template_name:
            raise ValidationError(
                "1 validation error detected: "
                "Value null at 'template.templateName'"
                "failed to satisfy constraint: Member must not be null"
            )

        if not self.templates.get(template_name, None):
            raise TemplateDoesNotExist("Invalid Template Name.")

        template_subject = template_info["subject_part"]
        if not template_subject:
            raise InvalidParameterValue("The subject must be specified.")
        self.templates[template_name] = template_info

    def get_template(self, template_name):
        if not self.templates.get(template_name, None):
            raise TemplateDoesNotExist("Invalid Template Name.")
        return self.templates[template_name]

    def list_templates(self):
        return list(self.templates.values())

    def render_template(self, render_data):
        template_name = render_data.get("name", "")
        template = self.templates.get(template_name, None)
        if not template:
            raise TemplateDoesNotExist("Invalid Template Name.")

        template_data = render_data.get("data")
        try:
            template_data = json.loads(template_data)
        except ValueError:
            raise InvalidRenderingParameterException(
                "Template rendering data is invalid"
            )

        var, are_variables_present = are_all_variables_present(template, template_data)
        if not are_variables_present:
            raise MissingRenderingAttributeException(var)

        subject_part = template["subject_part"]
        text_part = template["text_part"]
        html_part = template["html_part"]

        for key, value in template_data.items():
            subject_part = str.replace(str(subject_part), "{{%s}}" % key, value)
            text_part = str.replace(str(text_part), "{{%s}}" % key, value)
            html_part = str.replace(str(html_part), "{{%s}}" % key, value)

        email = MIMEMultipart("alternative")

        mime_text = MIMEBase("text", "plain;charset=UTF-8")
        mime_text.set_payload(text_part.encode("utf-8"))
        encode_7or8bit(mime_text)
        email.attach(mime_text)

        mime_html = MIMEBase("text", "html;charset=UTF-8")
        mime_html.set_payload(html_part.encode("utf-8"))
        encode_7or8bit(mime_html)
        email.attach(mime_html)

        now = datetime.datetime.now().isoformat()

        rendered_template = "Date: %s\r\nSubject: %s\r\n%s" % (
            now,
            subject_part,
            email.as_string(),
        )
        return rendered_template

    def create_receipt_rule_set(self, rule_set_name):
        if self.receipt_rule_set.get(rule_set_name) is not None:
            raise RuleSetNameAlreadyExists("Duplicate receipt rule set Name.")
        self.receipt_rule_set[rule_set_name] = []

    def create_receipt_rule(self, rule_set_name, rule):
        rule_set = self.receipt_rule_set.get(rule_set_name)
        if rule_set is None:
            raise RuleSetDoesNotExist("Invalid Rule Set Name.")
        if rule in rule_set:
            raise RuleAlreadyExists("Duplicate Rule Name.")
        rule_set.append(rule)
        self.receipt_rule_set[rule_set_name] = rule_set


ses_backend = SESBackend()
