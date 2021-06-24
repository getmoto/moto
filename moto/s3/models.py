# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
import base64
import datetime
import pytz
import hashlib
import copy
import itertools
import codecs
import random
import string
import tempfile
import threading
import sys
import time
import uuid

import six

from bisect import insort
from moto.core import ACCOUNT_ID, BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import iso_8601_datetime_without_milliseconds_s3, rfc_1123_datetime
from moto.cloudwatch.models import MetricDatum
from moto.utilities.tagging_service import TaggingService
from .exceptions import (
    BucketAlreadyExists,
    MissingBucket,
    InvalidBucketName,
    InvalidPart,
    InvalidRequest,
    EntityTooSmall,
    MissingKey,
    InvalidNotificationDestination,
    MalformedXML,
    InvalidStorageClass,
    InvalidTargetBucketForLogging,
    CrossLocationLoggingProhibitted,
    NoSuchPublicAccessBlockConfiguration,
    InvalidPublicAccessBlockConfiguration,
    WrongPublicAccessBlockAccountIdError,
    NoSuchUpload,
)
from .cloud_formation import cfn_to_api_encryption, is_replacement_update
from .utils import clean_key_name, _VersionedKeyStore
from ..settings import get_s3_default_key_buffer_size

MAX_BUCKET_NAME_LENGTH = 63
MIN_BUCKET_NAME_LENGTH = 3
UPLOAD_ID_BYTES = 43
UPLOAD_PART_MIN_SIZE = 5242880
STORAGE_CLASS = [
    "STANDARD",
    "REDUCED_REDUNDANCY",
    "STANDARD_IA",
    "ONEZONE_IA",
    "INTELLIGENT_TIERING",
    "GLACIER",
    "DEEP_ARCHIVE",
]
DEFAULT_TEXT_ENCODING = sys.getdefaultencoding()
OWNER = "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a"


def get_moto_s3_account_id():
    """This makes it easy for mocking AWS Account IDs when using AWS Config
    -- Simply mock.patch the ACCOUNT_ID here, and Config gets it for free.
    """
    return ACCOUNT_ID


class FakeDeleteMarker(BaseModel):
    def __init__(self, key):
        self.key = key
        self.name = key.name
        self.last_modified = datetime.datetime.utcnow()
        self._version_id = str(uuid.uuid4())

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime_without_milliseconds_s3(self.last_modified)

    @property
    def version_id(self):
        return self._version_id


class FakeKey(BaseModel):
    def __init__(
        self,
        name,
        value,
        storage="STANDARD",
        etag=None,
        is_versioned=False,
        version_id=0,
        max_buffer_size=None,
        multipart=None,
        bucket_name=None,
        encryption=None,
        kms_key_id=None,
        bucket_key_enabled=None,
    ):
        self.name = name
        self.last_modified = datetime.datetime.utcnow()
        self.acl = get_canned_acl("private")
        self.website_redirect_location = None
        self._storage_class = storage if storage else "STANDARD"
        self._metadata = {}
        self._expiry = None
        self._etag = etag
        self._version_id = version_id
        self._is_versioned = is_versioned
        self.multipart = multipart
        self.bucket_name = bucket_name

        self._max_buffer_size = (
            max_buffer_size if max_buffer_size else get_s3_default_key_buffer_size()
        )
        self._value_buffer = tempfile.SpooledTemporaryFile(self._max_buffer_size)
        self.value = value
        self.lock = threading.Lock()

        self.encryption = encryption
        self.kms_key_id = kms_key_id
        self.bucket_key_enabled = bucket_key_enabled

    @property
    def version_id(self):
        return self._version_id

    @property
    def value(self):
        self.lock.acquire()
        self._value_buffer.seek(0)
        r = self._value_buffer.read()
        r = copy.copy(r)
        self.lock.release()
        return r

    @property
    def arn(self):
        # S3 Objects don't have an ARN, but we do need something unique when creating tags against this resource
        return "arn:aws:s3:::{}/{}/{}".format(
            self.bucket_name, self.name, self.version_id
        )

    @value.setter
    def value(self, new_value):
        self._value_buffer.seek(0)
        self._value_buffer.truncate()

        # Hack for working around moto's own unit tests; this probably won't
        # actually get hit in normal use.
        if isinstance(new_value, six.text_type):
            new_value = new_value.encode(DEFAULT_TEXT_ENCODING)
        self._value_buffer.write(new_value)
        self.contentsize = len(new_value)

    def copy(self, new_name=None, new_is_versioned=None):
        r = copy.deepcopy(self)
        if new_name is not None:
            r.name = new_name
        if new_is_versioned is not None:
            r._is_versioned = new_is_versioned
            r.refresh_version()
        return r

    def set_metadata(self, metadata, replace=False):
        if replace:
            self._metadata = {}
        self._metadata.update(metadata)

    def set_storage_class(self, storage):
        if storage is not None and storage not in STORAGE_CLASS:
            raise InvalidStorageClass(storage=storage)
        self._storage_class = storage

    def set_expiry(self, expiry):
        self._expiry = expiry

    def set_acl(self, acl):
        self.acl = acl

    def append_to_value(self, value):
        self.contentsize += len(value)
        self._value_buffer.seek(0, os.SEEK_END)
        self._value_buffer.write(value)

        self.last_modified = datetime.datetime.utcnow()
        self._etag = None  # must recalculate etag
        if self._is_versioned:
            self._version_id = str(uuid.uuid4())
        else:
            self._version_id = None

    def restore(self, days):
        self._expiry = datetime.datetime.utcnow() + datetime.timedelta(days)

    def refresh_version(self):
        self._version_id = str(uuid.uuid4())
        self.last_modified = datetime.datetime.utcnow()

    @property
    def etag(self):
        if self._etag is None:
            value_md5 = hashlib.md5()
            self._value_buffer.seek(0)
            while True:
                block = self._value_buffer.read(16 * 1024 * 1024)  # read in 16MB chunks
                if not block:
                    break
                value_md5.update(block)

            self._etag = value_md5.hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime_without_milliseconds_s3(self.last_modified)

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return rfc_1123_datetime(self.last_modified)

    @property
    def metadata(self):
        return self._metadata

    @property
    def response_dict(self):
        res = {
            "ETag": self.etag,
            "last-modified": self.last_modified_RFC1123,
            "content-length": str(self.size),
        }
        if self.encryption is not None:
            res["x-amz-server-side-encryption"] = self.encryption
            if self.encryption == "aws:kms" and self.kms_key_id is not None:
                res["x-amz-server-side-encryption-aws-kms-key-id"] = self.kms_key_id
        if self.bucket_key_enabled is not None:
            res[
                "x-amz-server-side-encryption-bucket-key-enabled"
            ] = self.bucket_key_enabled
        if self._storage_class != "STANDARD":
            res["x-amz-storage-class"] = self._storage_class
        if self._expiry is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            res["x-amz-restore"] = rhdr.format(self.expiry_date)

        if self._is_versioned:
            res["x-amz-version-id"] = str(self.version_id)

        if self.website_redirect_location:
            res["x-amz-website-redirect-location"] = self.website_redirect_location

        return res

    @property
    def size(self):
        return self.contentsize

    @property
    def storage_class(self):
        return self._storage_class

    @property
    def expiry_date(self):
        if self._expiry is not None:
            return self._expiry.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Keys need to be pickleable due to some implementation details of boto3.
    # Since file objects aren't pickleable, we need to override the default
    # behavior. The following is adapted from the Python docs:
    # https://docs.python.org/3/library/pickle.html#handling-stateful-objects
    def __getstate__(self):
        state = self.__dict__.copy()
        state["value"] = self.value
        del state["_value_buffer"]
        del state["lock"]
        return state

    def __setstate__(self, state):
        self.__dict__.update({k: v for k, v in six.iteritems(state) if k != "value"})

        self._value_buffer = tempfile.SpooledTemporaryFile(
            max_size=self._max_buffer_size
        )
        self.value = state["value"]
        self.lock = threading.Lock()


class FakeMultipart(BaseModel):
    def __init__(self, key_name, metadata):
        self.key_name = key_name
        self.metadata = metadata
        self.parts = {}
        self.partlist = []  # ordered list of part ID's
        rand_b64 = base64.b64encode(os.urandom(UPLOAD_ID_BYTES))
        self.id = (
            rand_b64.decode("utf-8").replace("=", "").replace("+", "").replace("/", "")
        )

    def complete(self, body):
        decode_hex = codecs.getdecoder("hex_codec")
        total = bytearray()
        md5s = bytearray()

        last = None
        count = 0
        for pn, etag in body:
            part = self.parts.get(pn)
            part_etag = None
            if part is not None:
                part_etag = part.etag.replace('"', "")
                etag = etag.replace('"', "")
            if part is None or part_etag != etag:
                raise InvalidPart()
            if last is not None and last.contentsize < UPLOAD_PART_MIN_SIZE:
                raise EntityTooSmall()
            md5s.extend(decode_hex(part_etag)[0])
            total.extend(part.value)
            last = part
            count += 1

        etag = hashlib.md5()
        etag.update(bytes(md5s))
        return total, "{0}-{1}".format(etag.hexdigest(), count)

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        key = FakeKey(part_id, value)
        self.parts[part_id] = key
        if part_id not in self.partlist:
            insort(self.partlist, part_id)
        return key

    def list_parts(self):
        for part_id in self.partlist:
            yield self.parts[part_id]


class FakeGrantee(BaseModel):
    def __init__(self, id="", uri="", display_name=""):
        self.id = id
        self.uri = uri
        self.display_name = display_name

    def __eq__(self, other):
        if not isinstance(other, FakeGrantee):
            return False
        return (
            self.id == other.id
            and self.uri == other.uri
            and self.display_name == other.display_name
        )

    @property
    def type(self):
        return "Group" if self.uri else "CanonicalUser"

    def __repr__(self):
        return "FakeGrantee(display_name: '{}', id: '{}', uri: '{}')".format(
            self.display_name, self.id, self.uri
        )


ALL_USERS_GRANTEE = FakeGrantee(uri="http://acs.amazonaws.com/groups/global/AllUsers")
AUTHENTICATED_USERS_GRANTEE = FakeGrantee(
    uri="http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
)
LOG_DELIVERY_GRANTEE = FakeGrantee(uri="http://acs.amazonaws.com/groups/s3/LogDelivery")

PERMISSION_FULL_CONTROL = "FULL_CONTROL"
PERMISSION_WRITE = "WRITE"
PERMISSION_READ = "READ"
PERMISSION_WRITE_ACP = "WRITE_ACP"
PERMISSION_READ_ACP = "READ_ACP"

CAMEL_CASED_PERMISSIONS = {
    "FULL_CONTROL": "FullControl",
    "WRITE": "Write",
    "READ": "Read",
    "WRITE_ACP": "WriteAcp",
    "READ_ACP": "ReadAcp",
}


class FakeGrant(BaseModel):
    def __init__(self, grantees, permissions):
        self.grantees = grantees
        self.permissions = permissions

    def __repr__(self):
        return "FakeGrant(grantees: {}, permissions: {})".format(
            self.grantees, self.permissions
        )


class FakeAcl(BaseModel):
    def __init__(self, grants=None):
        grants = grants or []
        self.grants = grants

    @property
    def public_read(self):
        for grant in self.grants:
            if ALL_USERS_GRANTEE in grant.grantees:
                if PERMISSION_READ in grant.permissions:
                    return True
                if PERMISSION_FULL_CONTROL in grant.permissions:
                    return True
        return False

    def __repr__(self):
        return "FakeAcl(grants: {})".format(self.grants)

    def to_config_dict(self):
        """Returns the object into the format expected by AWS Config"""
        data = {
            "grantSet": None,  # Always setting this to None. Feel free to change.
            "owner": {"displayName": None, "id": OWNER},
        }

        # Add details for each Grant:
        grant_list = []
        for grant in self.grants:
            permissions = (
                grant.permissions
                if isinstance(grant.permissions, list)
                else [grant.permissions]
            )
            for permission in permissions:
                for grantee in grant.grantees:
                    if grantee.uri:
                        grant_list.append(
                            {
                                "grantee": grantee.uri.split(
                                    "http://acs.amazonaws.com/groups/s3/"
                                )[1],
                                "permission": CAMEL_CASED_PERMISSIONS[permission],
                            }
                        )
                    else:
                        grant_list.append(
                            {
                                "grantee": {
                                    "id": grantee.id,
                                    "displayName": None
                                    if not grantee.display_name
                                    else grantee.display_name,
                                },
                                "permission": CAMEL_CASED_PERMISSIONS[permission],
                            }
                        )

        if grant_list:
            data["grantList"] = grant_list

        return data


def get_canned_acl(acl):
    owner_grantee = FakeGrantee(id=OWNER)
    grants = [FakeGrant([owner_grantee], [PERMISSION_FULL_CONTROL])]
    if acl == "private":
        pass  # no other permissions
    elif acl == "public-read":
        grants.append(FakeGrant([ALL_USERS_GRANTEE], [PERMISSION_READ]))
    elif acl == "public-read-write":
        grants.append(
            FakeGrant([ALL_USERS_GRANTEE], [PERMISSION_READ, PERMISSION_WRITE])
        )
    elif acl == "authenticated-read":
        grants.append(FakeGrant([AUTHENTICATED_USERS_GRANTEE], [PERMISSION_READ]))
    elif acl == "bucket-owner-read":
        pass  # TODO: bucket owner ACL
    elif acl == "bucket-owner-full-control":
        pass  # TODO: bucket owner ACL
    elif acl == "aws-exec-read":
        pass  # TODO: bucket owner, EC2 Read
    elif acl == "log-delivery-write":
        grants.append(
            FakeGrant([LOG_DELIVERY_GRANTEE], [PERMISSION_READ_ACP, PERMISSION_WRITE])
        )
    else:
        assert False, "Unknown canned acl: %s" % (acl,)
    return FakeAcl(grants=grants)


class LifecycleFilter(BaseModel):
    def __init__(self, prefix=None, tag=None, and_filter=None):
        self.prefix = prefix
        (self.tag_key, self.tag_value) = tag if tag else (None, None)
        self.and_filter = and_filter

    def to_config_dict(self):
        if self.prefix is not None:
            return {
                "predicate": {"type": "LifecyclePrefixPredicate", "prefix": self.prefix}
            }

        elif self.tag_key:
            return {
                "predicate": {
                    "type": "LifecycleTagPredicate",
                    "tag": {"key": self.tag_key, "value": self.tag_value},
                }
            }

        else:
            return {
                "predicate": {
                    "type": "LifecycleAndOperator",
                    "operands": self.and_filter.to_config_dict(),
                }
            }


class LifecycleAndFilter(BaseModel):
    def __init__(self, prefix=None, tags=None):
        self.prefix = prefix
        self.tags = tags

    def to_config_dict(self):
        data = []

        if self.prefix is not None:
            data.append({"type": "LifecyclePrefixPredicate", "prefix": self.prefix})

        for key, value in self.tags.items():
            data.append(
                {"type": "LifecycleTagPredicate", "tag": {"key": key, "value": value},}
            )

        return data


class LifecycleRule(BaseModel):
    def __init__(
        self,
        id=None,
        prefix=None,
        lc_filter=None,
        status=None,
        expiration_days=None,
        expiration_date=None,
        transition_days=None,
        transition_date=None,
        storage_class=None,
        expired_object_delete_marker=None,
        nve_noncurrent_days=None,
        nvt_noncurrent_days=None,
        nvt_storage_class=None,
        aimu_days=None,
    ):
        self.id = id
        self.prefix = prefix
        self.filter = lc_filter
        self.status = status
        self.expiration_days = expiration_days
        self.expiration_date = expiration_date
        self.transition_days = transition_days
        self.transition_date = transition_date
        self.storage_class = storage_class
        self.expired_object_delete_marker = expired_object_delete_marker
        self.nve_noncurrent_days = nve_noncurrent_days
        self.nvt_noncurrent_days = nvt_noncurrent_days
        self.nvt_storage_class = nvt_storage_class
        self.aimu_days = aimu_days

    def to_config_dict(self):
        """Converts the object to the AWS Config data dict.

        Note: The following are missing that should be added in the future:
            - transitions (returns None for now)
            - noncurrentVersionTransitions (returns None for now)

        :param kwargs:
        :return:
        """

        lifecycle_dict = {
            "id": self.id,
            "prefix": self.prefix,
            "status": self.status,
            "expirationInDays": int(self.expiration_days)
            if self.expiration_days
            else None,
            "expiredObjectDeleteMarker": self.expired_object_delete_marker,
            "noncurrentVersionExpirationInDays": -1 or int(self.nve_noncurrent_days),
            "expirationDate": self.expiration_date,
            "transitions": None,  # Replace me with logic to fill in
            "noncurrentVersionTransitions": None,  # Replace me with logic to fill in
        }

        if self.aimu_days:
            lifecycle_dict["abortIncompleteMultipartUpload"] = {
                "daysAfterInitiation": self.aimu_days
            }
        else:
            lifecycle_dict["abortIncompleteMultipartUpload"] = None

        # Format the filter:
        if self.prefix is None and self.filter is None:
            lifecycle_dict["filter"] = {"predicate": None}

        elif self.prefix:
            lifecycle_dict["filter"] = None
        else:
            lifecycle_dict["filter"] = self.filter.to_config_dict()

        return lifecycle_dict


class CorsRule(BaseModel):
    def __init__(
        self,
        allowed_methods,
        allowed_origins,
        allowed_headers=None,
        expose_headers=None,
        max_age_seconds=None,
    ):
        self.allowed_methods = (
            [allowed_methods]
            if isinstance(allowed_methods, six.string_types)
            else allowed_methods
        )
        self.allowed_origins = (
            [allowed_origins]
            if isinstance(allowed_origins, six.string_types)
            else allowed_origins
        )
        self.allowed_headers = (
            [allowed_headers]
            if isinstance(allowed_headers, six.string_types)
            else allowed_headers
        )
        self.exposed_headers = (
            [expose_headers]
            if isinstance(expose_headers, six.string_types)
            else expose_headers
        )
        self.max_age_seconds = max_age_seconds


class Notification(BaseModel):
    def __init__(self, arn, events, filters=None, id=None):
        self.id = (
            id
            if id
            else "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(50)
            )
        )
        self.arn = arn
        self.events = events
        self.filters = filters if filters else {}

    def to_config_dict(self):
        data = {}

        # Type and ARN will be filled in by NotificationConfiguration's to_config_dict:
        data["events"] = [event for event in self.events]

        if self.filters:
            data["filter"] = {
                "s3KeyFilter": {
                    "filterRules": [
                        {"name": fr["Name"], "value": fr["Value"]}
                        for fr in self.filters["S3Key"]["FilterRule"]
                    ]
                }
            }
        else:
            data["filter"] = None

        # Not sure why this is a thing since AWS just seems to return this as filters ¯\_(ツ)_/¯
        data["objectPrefixes"] = []

        return data


class NotificationConfiguration(BaseModel):
    def __init__(self, topic=None, queue=None, cloud_function=None):
        self.topic = (
            [
                Notification(
                    t["Topic"], t["Event"], filters=t.get("Filter"), id=t.get("Id")
                )
                for t in topic
            ]
            if topic
            else []
        )
        self.queue = (
            [
                Notification(
                    q["Queue"], q["Event"], filters=q.get("Filter"), id=q.get("Id")
                )
                for q in queue
            ]
            if queue
            else []
        )
        self.cloud_function = (
            [
                Notification(
                    c["CloudFunction"],
                    c["Event"],
                    filters=c.get("Filter"),
                    id=c.get("Id"),
                )
                for c in cloud_function
            ]
            if cloud_function
            else []
        )

    def to_config_dict(self):
        data = {"configurations": {}}

        for topic in self.topic:
            topic_config = topic.to_config_dict()
            topic_config["topicARN"] = topic.arn
            topic_config["type"] = "TopicConfiguration"
            data["configurations"][topic.id] = topic_config

        for queue in self.queue:
            queue_config = queue.to_config_dict()
            queue_config["queueARN"] = queue.arn
            queue_config["type"] = "QueueConfiguration"
            data["configurations"][queue.id] = queue_config

        for cloud_function in self.cloud_function:
            cf_config = cloud_function.to_config_dict()
            cf_config["queueARN"] = cloud_function.arn
            cf_config["type"] = "LambdaConfiguration"
            data["configurations"][cloud_function.id] = cf_config

        return data


def convert_str_to_bool(item):
    """Converts a boolean string to a boolean value"""
    if isinstance(item, str):
        return item.lower() == "true"

    return False


class PublicAccessBlock(BaseModel):
    def __init__(
        self,
        block_public_acls,
        ignore_public_acls,
        block_public_policy,
        restrict_public_buckets,
    ):
        # The boto XML appears to expect these values to exist as lowercase strings...
        self.block_public_acls = block_public_acls or "false"
        self.ignore_public_acls = ignore_public_acls or "false"
        self.block_public_policy = block_public_policy or "false"
        self.restrict_public_buckets = restrict_public_buckets or "false"

    def to_config_dict(self):
        # Need to make the string values booleans for Config:
        return {
            "blockPublicAcls": convert_str_to_bool(self.block_public_acls),
            "ignorePublicAcls": convert_str_to_bool(self.ignore_public_acls),
            "blockPublicPolicy": convert_str_to_bool(self.block_public_policy),
            "restrictPublicBuckets": convert_str_to_bool(self.restrict_public_buckets),
        }


class FakeBucket(CloudFormationModel):
    def __init__(self, name, region_name):
        self.name = name
        self.region_name = region_name
        self.keys = _VersionedKeyStore()
        self.multiparts = {}
        self.versioning_status = None
        self.rules = []
        self.policy = None
        self.website_configuration = None
        self.acl = get_canned_acl("private")
        self.cors = []
        self.logging = {}
        self.notification_configuration = None
        self.accelerate_configuration = None
        self.payer = "BucketOwner"
        self.creation_date = datetime.datetime.now(tz=pytz.utc)
        self.public_access_block = None
        self.encryption = None

    @property
    def location(self):
        return self.region_name

    @property
    def creation_date_ISO8601(self):
        return iso_8601_datetime_without_milliseconds_s3(self.creation_date)

    @property
    def is_versioned(self):
        return self.versioning_status == "Enabled"

    def set_lifecycle(self, rules):
        self.rules = []
        for rule in rules:
            # Extract and validate actions from Lifecycle rule
            expiration = rule.get("Expiration")
            transition = rule.get("Transition")

            try:
                top_level_prefix = (
                    rule["Prefix"] or ""
                )  # If it's `None` the set to the empty string
            except KeyError:
                top_level_prefix = None

            nve_noncurrent_days = None
            if rule.get("NoncurrentVersionExpiration") is not None:
                if rule["NoncurrentVersionExpiration"].get("NoncurrentDays") is None:
                    raise MalformedXML()
                nve_noncurrent_days = rule["NoncurrentVersionExpiration"][
                    "NoncurrentDays"
                ]

            nvt_noncurrent_days = None
            nvt_storage_class = None
            if rule.get("NoncurrentVersionTransition") is not None:
                if rule["NoncurrentVersionTransition"].get("NoncurrentDays") is None:
                    raise MalformedXML()
                if rule["NoncurrentVersionTransition"].get("StorageClass") is None:
                    raise MalformedXML()
                nvt_noncurrent_days = rule["NoncurrentVersionTransition"][
                    "NoncurrentDays"
                ]
                nvt_storage_class = rule["NoncurrentVersionTransition"]["StorageClass"]

            aimu_days = None
            if rule.get("AbortIncompleteMultipartUpload") is not None:
                if (
                    rule["AbortIncompleteMultipartUpload"].get("DaysAfterInitiation")
                    is None
                ):
                    raise MalformedXML()
                aimu_days = rule["AbortIncompleteMultipartUpload"][
                    "DaysAfterInitiation"
                ]

            eodm = None
            if expiration and expiration.get("ExpiredObjectDeleteMarker") is not None:
                # This cannot be set if Date or Days is set:
                if expiration.get("Days") or expiration.get("Date"):
                    raise MalformedXML()
                eodm = expiration["ExpiredObjectDeleteMarker"]

            # Pull out the filter:
            lc_filter = None
            if rule.get("Filter"):
                # Can't have both `Filter` and `Prefix` (need to check for the presence of the key):
                try:
                    # 'Prefix' cannot be outside of a Filter:
                    if rule["Prefix"] or not rule["Prefix"]:
                        raise MalformedXML()
                except KeyError:
                    pass

                filters = 0
                try:
                    prefix_filter = (
                        rule["Filter"]["Prefix"] or ""
                    )  # If it's `None` the set to the empty string
                    filters += 1
                except KeyError:
                    prefix_filter = None

                and_filter = None
                if rule["Filter"].get("And"):
                    filters += 1
                    and_tags = {}
                    if rule["Filter"]["And"].get("Tag"):
                        if not isinstance(rule["Filter"]["And"]["Tag"], list):
                            rule["Filter"]["And"]["Tag"] = [
                                rule["Filter"]["And"]["Tag"]
                            ]

                        for t in rule["Filter"]["And"]["Tag"]:
                            and_tags[t["Key"]] = t.get("Value", "")

                    try:
                        and_prefix = (
                            rule["Filter"]["And"]["Prefix"] or ""
                        )  # If it's `None` then set to the empty string
                    except KeyError:
                        and_prefix = None

                    and_filter = LifecycleAndFilter(prefix=and_prefix, tags=and_tags)

                filter_tag = None
                if rule["Filter"].get("Tag"):
                    filters += 1
                    filter_tag = (
                        rule["Filter"]["Tag"]["Key"],
                        rule["Filter"]["Tag"].get("Value", ""),
                    )

                # Can't have more than 1 filter:
                if filters > 1:
                    raise MalformedXML()

                lc_filter = LifecycleFilter(
                    prefix=prefix_filter, tag=filter_tag, and_filter=and_filter
                )

            # If no top level prefix and no filter is present, then this is invalid:
            if top_level_prefix is None:
                try:
                    rule["Filter"]
                except KeyError:
                    raise MalformedXML()

            self.rules.append(
                LifecycleRule(
                    id=rule.get("ID"),
                    prefix=top_level_prefix,
                    lc_filter=lc_filter,
                    status=rule["Status"],
                    expiration_days=expiration.get("Days") if expiration else None,
                    expiration_date=expiration.get("Date") if expiration else None,
                    transition_days=transition.get("Days") if transition else None,
                    transition_date=transition.get("Date") if transition else None,
                    storage_class=transition.get("StorageClass")
                    if transition
                    else None,
                    expired_object_delete_marker=eodm,
                    nve_noncurrent_days=nve_noncurrent_days,
                    nvt_noncurrent_days=nvt_noncurrent_days,
                    nvt_storage_class=nvt_storage_class,
                    aimu_days=aimu_days,
                )
            )

    def delete_lifecycle(self):
        self.rules = []

    def set_cors(self, rules):
        self.cors = []

        if len(rules) > 100:
            raise MalformedXML()

        for rule in rules:
            assert isinstance(rule["AllowedMethod"], list) or isinstance(
                rule["AllowedMethod"], six.string_types
            )
            assert isinstance(rule["AllowedOrigin"], list) or isinstance(
                rule["AllowedOrigin"], six.string_types
            )
            assert isinstance(rule.get("AllowedHeader", []), list) or isinstance(
                rule.get("AllowedHeader", ""), six.string_types
            )
            assert isinstance(rule.get("ExposedHeader", []), list) or isinstance(
                rule.get("ExposedHeader", ""), six.string_types
            )
            assert isinstance(rule.get("MaxAgeSeconds", "0"), six.string_types)

            if isinstance(rule["AllowedMethod"], six.string_types):
                methods = [rule["AllowedMethod"]]
            else:
                methods = rule["AllowedMethod"]

            for method in methods:
                if method not in ["GET", "PUT", "HEAD", "POST", "DELETE"]:
                    raise InvalidRequest(method)

            self.cors.append(
                CorsRule(
                    rule["AllowedMethod"],
                    rule["AllowedOrigin"],
                    rule.get("AllowedHeader"),
                    rule.get("ExposedHeader"),
                    rule.get("MaxAgeSecond"),
                )
            )

    def delete_cors(self):
        self.cors = []

    def set_logging(self, logging_config, bucket_backend):
        if not logging_config:
            self.logging = {}
            return

        # Target bucket must exist in the same account (assuming all moto buckets are in the same account):
        if not bucket_backend.buckets.get(logging_config["TargetBucket"]):
            raise InvalidTargetBucketForLogging(
                "The target bucket for logging does not exist."
            )

        # Does the target bucket have the log-delivery WRITE and READ_ACP permissions?
        write = read_acp = False
        for grant in bucket_backend.buckets[logging_config["TargetBucket"]].acl.grants:
            # Must be granted to: http://acs.amazonaws.com/groups/s3/LogDelivery
            for grantee in grant.grantees:
                if grantee.uri == "http://acs.amazonaws.com/groups/s3/LogDelivery":
                    if (
                        "WRITE" in grant.permissions
                        or "FULL_CONTROL" in grant.permissions
                    ):
                        write = True

                    if (
                        "READ_ACP" in grant.permissions
                        or "FULL_CONTROL" in grant.permissions
                    ):
                        read_acp = True

                    break

        if not write or not read_acp:
            raise InvalidTargetBucketForLogging(
                "You must give the log-delivery group WRITE and READ_ACP"
                " permissions to the target bucket"
            )

        # Buckets must also exist within the same region:
        if (
            bucket_backend.buckets[logging_config["TargetBucket"]].region_name
            != self.region_name
        ):
            raise CrossLocationLoggingProhibitted()

        # Checks pass -- set the logging config:
        self.logging = logging_config

    def set_notification_configuration(self, notification_config):
        if not notification_config:
            self.notification_configuration = None
            return

        self.notification_configuration = NotificationConfiguration(
            topic=notification_config.get("TopicConfiguration"),
            queue=notification_config.get("QueueConfiguration"),
            cloud_function=notification_config.get("CloudFunctionConfiguration"),
        )

        # Validate that the region is correct:
        for thing in ["topic", "queue", "cloud_function"]:
            for t in getattr(self.notification_configuration, thing):
                region = t.arn.split(":")[3]
                if region != self.region_name:
                    raise InvalidNotificationDestination()

    def set_accelerate_configuration(self, accelerate_config):
        if self.accelerate_configuration is None and accelerate_config == "Suspended":
            # Cannot "suspend" a not active acceleration. Leaves it undefined
            return

        self.accelerate_configuration = accelerate_config

    def set_website_configuration(self, website_configuration):
        self.website_configuration = website_configuration

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        elif attribute_name == "DomainName":
            return self.domain_name
        elif attribute_name == "DualStackDomainName":
            return self.dual_stack_domain_name
        elif attribute_name == "RegionalDomainName":
            return self.regional_domain_name
        elif attribute_name == "WebsiteURL":
            return self.website_url
        raise UnformattedGetAttTemplateException()

    def set_acl(self, acl):
        self.acl = acl

    @property
    def arn(self):
        return "arn:aws:s3:::{}".format(self.name)

    @property
    def domain_name(self):
        return "{}.s3.amazonaws.com".format(self.name)

    @property
    def dual_stack_domain_name(self):
        return "{}.s3.dualstack.{}.amazonaws.com".format(self.name, self.region_name)

    @property
    def regional_domain_name(self):
        return "{}.s3.{}.amazonaws.com".format(self.name, self.region_name)

    @property
    def website_url(self):
        return "http://{}.s3-website.{}.amazonaws.com".format(
            self.name, self.region_name
        )

    @property
    def physical_resource_id(self):
        return self.name

    @staticmethod
    def cloudformation_name_type():
        return "BucketName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-s3-bucket.html
        return "AWS::S3::Bucket"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        bucket = s3_backend.create_bucket(resource_name, region_name)

        properties = cloudformation_json.get("Properties", {})

        if "BucketEncryption" in properties:
            bucket_encryption = cfn_to_api_encryption(properties["BucketEncryption"])
            s3_backend.put_bucket_encryption(
                bucket_name=resource_name, encryption=[bucket_encryption]
            )

        return bucket

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name,
    ):
        properties = cloudformation_json["Properties"]

        if is_replacement_update(properties):
            resource_name_property = cls.cloudformation_name_type()
            if resource_name_property not in properties:
                properties[resource_name_property] = new_resource_name
            new_resource = cls.create_from_cloudformation_json(
                properties[resource_name_property], cloudformation_json, region_name
            )
            properties[resource_name_property] = original_resource.name
            cls.delete_from_cloudformation_json(
                original_resource.name, cloudformation_json, region_name
            )
            return new_resource

        else:  # No Interruption
            if "BucketEncryption" in properties:
                bucket_encryption = cfn_to_api_encryption(
                    properties["BucketEncryption"]
                )
                s3_backend.put_bucket_encryption(
                    bucket_name=original_resource.name, encryption=[bucket_encryption]
                )
            return original_resource

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        s3_backend.delete_bucket(resource_name)

    def to_config_dict(self):
        """Return the AWS Config JSON format of this S3 bucket.

        Note: The following features are not implemented and will need to be if you care about them:
        - Bucket Accelerate Configuration
        """
        config_dict = {
            "version": "1.3",
            "configurationItemCaptureTime": str(self.creation_date),
            "configurationItemStatus": "ResourceDiscovered",
            "configurationStateId": str(
                int(time.mktime(self.creation_date.timetuple()))
            ),  # PY2 and 3 compatible
            "configurationItemMD5Hash": "",
            "arn": self.arn,
            "resourceType": "AWS::S3::Bucket",
            "resourceId": self.name,
            "resourceName": self.name,
            "awsRegion": self.region_name,
            "availabilityZone": "Regional",
            "resourceCreationTime": str(self.creation_date),
            "relatedEvents": [],
            "relationships": [],
            "tags": s3_backend.tagger.get_tag_dict_for_resource(self.arn),
            "configuration": {
                "name": self.name,
                "owner": {"id": OWNER},
                "creationDate": self.creation_date.isoformat(),
            },
        }

        # Make the supplementary configuration:
        # This is a dobule-wrapped JSON for some reason...
        s_config = {
            "AccessControlList": json.dumps(json.dumps(self.acl.to_config_dict()))
        }

        if self.public_access_block:
            s_config["PublicAccessBlockConfiguration"] = json.dumps(
                self.public_access_block.to_config_dict()
            )

        # Tagging is special:
        if config_dict["tags"]:
            s_config["BucketTaggingConfiguration"] = json.dumps(
                {"tagSets": [{"tags": config_dict["tags"]}]}
            )

        # TODO implement Accelerate Configuration:
        s_config["BucketAccelerateConfiguration"] = {"status": None}

        if self.rules:
            s_config["BucketLifecycleConfiguration"] = {
                "rules": [rule.to_config_dict() for rule in self.rules]
            }

        s_config["BucketLoggingConfiguration"] = {
            "destinationBucketName": self.logging.get("TargetBucket", None),
            "logFilePrefix": self.logging.get("TargetPrefix", None),
        }

        s_config["BucketPolicy"] = {
            "policyText": self.policy.decode("utf-8") if self.policy else None
        }

        s_config["IsRequesterPaysEnabled"] = (
            "false" if self.payer == "BucketOwner" else "true"
        )

        if self.notification_configuration:
            s_config[
                "BucketNotificationConfiguration"
            ] = self.notification_configuration.to_config_dict()
        else:
            s_config["BucketNotificationConfiguration"] = {"configurations": {}}

        config_dict["supplementaryConfiguration"] = s_config

        return config_dict


class S3Backend(BaseBackend):
    def __init__(self):
        self.buckets = {}
        self.account_public_access_block = None
        self.tagger = TaggingService()

        # TODO: This is broken! DO NOT IMPORT MUTABLE DATA TYPES FROM OTHER AREAS -- THIS BREAKS UNMOCKING!
        # WRAP WITH A GETTER/SETTER FUNCTION
        # Register this class as a CloudWatch Metric Provider
        # Must provide a method 'get_cloudwatch_metrics' that will return a list of metrics, based on the data available
        # metric_providers["S3"] = self

    def get_cloudwatch_metrics(self):
        metrics = []
        for name, bucket in self.buckets.items():
            metrics.append(
                MetricDatum(
                    namespace="AWS/S3",
                    name="BucketSizeBytes",
                    value=bucket.keys.item_size(),
                    dimensions=[
                        {"Name": "StorageType", "Value": "StandardStorage"},
                        {"Name": "BucketName", "Value": name},
                    ],
                    timestamp=datetime.datetime.now(),
                )
            )
            metrics.append(
                MetricDatum(
                    namespace="AWS/S3",
                    name="NumberOfObjects",
                    value=len(bucket.keys),
                    dimensions=[
                        {"Name": "StorageType", "Value": "AllStorageTypes"},
                        {"Name": "BucketName", "Value": name},
                    ],
                    timestamp=datetime.datetime.now(),
                )
            )
        return metrics

    def create_bucket(self, bucket_name, region_name):
        if bucket_name in self.buckets:
            raise BucketAlreadyExists(bucket=bucket_name)
        if not MIN_BUCKET_NAME_LENGTH <= len(bucket_name) <= MAX_BUCKET_NAME_LENGTH:
            raise InvalidBucketName()
        new_bucket = FakeBucket(name=bucket_name, region_name=region_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_all_buckets(self):
        return self.buckets.values()

    def get_bucket(self, bucket_name):
        try:
            return self.buckets[bucket_name]
        except KeyError:
            raise MissingBucket(bucket=bucket_name)

    def delete_bucket(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        if bucket.keys:
            # Can't delete a bucket with keys
            return False
        else:
            return self.buckets.pop(bucket_name)

    def set_bucket_versioning(self, bucket_name, status):
        self.get_bucket(bucket_name).versioning_status = status

    def get_bucket_versioning(self, bucket_name):
        return self.get_bucket(bucket_name).versioning_status

    def get_bucket_encryption(self, bucket_name):
        return self.get_bucket(bucket_name).encryption

    def get_bucket_latest_versions(self, bucket_name):
        versions = self.get_bucket_versions(bucket_name)
        latest_modified_per_key = {}
        latest_versions = {}

        for version in versions:
            name = version.name
            last_modified = version.last_modified
            version_id = version.version_id
            latest_modified_per_key[name] = max(
                last_modified, latest_modified_per_key.get(name, datetime.datetime.min)
            )
            if last_modified == latest_modified_per_key[name]:
                latest_versions[name] = version_id

        return latest_versions

    def get_bucket_versions(
        self,
        bucket_name,
        delimiter=None,
        encoding_type=None,
        key_marker=None,
        max_keys=None,
        version_id_marker=None,
        prefix="",
    ):
        bucket = self.get_bucket(bucket_name)

        if any((delimiter, key_marker, version_id_marker)):
            raise NotImplementedError(
                "Called get_bucket_versions with some of delimiter, encoding_type, key_marker, version_id_marker"
            )

        return itertools.chain(
            *(l for key, l in bucket.keys.iterlists() if key.startswith(prefix))
        )

    def get_bucket_policy(self, bucket_name):
        return self.get_bucket(bucket_name).policy

    def set_bucket_policy(self, bucket_name, policy):
        self.get_bucket(bucket_name).policy = policy

    def delete_bucket_policy(self, bucket_name, body):
        bucket = self.get_bucket(bucket_name)
        bucket.policy = None

    def put_bucket_encryption(self, bucket_name, encryption):
        self.get_bucket(bucket_name).encryption = encryption

    def delete_bucket_encryption(self, bucket_name):
        self.get_bucket(bucket_name).encryption = None

    def set_bucket_lifecycle(self, bucket_name, rules):
        bucket = self.get_bucket(bucket_name)
        bucket.set_lifecycle(rules)

    def set_bucket_website_configuration(self, bucket_name, website_configuration):
        bucket = self.get_bucket(bucket_name)
        bucket.set_website_configuration(website_configuration)

    def get_bucket_website_configuration(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.website_configuration

    def get_bucket_public_access_block(self, bucket_name):
        bucket = self.get_bucket(bucket_name)

        if not bucket.public_access_block:
            raise NoSuchPublicAccessBlockConfiguration()

        return bucket.public_access_block

    def get_account_public_access_block(self, account_id):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        if not self.account_public_access_block:
            raise NoSuchPublicAccessBlockConfiguration()

        return self.account_public_access_block

    def set_object(
        self,
        bucket_name,
        key_name,
        value,
        storage=None,
        etag=None,
        multipart=None,
        encryption=None,
        kms_key_id=None,
        bucket_key_enabled=None,
    ):
        key_name = clean_key_name(key_name)
        if storage is not None and storage not in STORAGE_CLASS:
            raise InvalidStorageClass(storage=storage)

        bucket = self.get_bucket(bucket_name)

        new_key = FakeKey(
            name=key_name,
            value=value,
            storage=storage,
            etag=etag,
            is_versioned=bucket.is_versioned,
            version_id=str(uuid.uuid4()) if bucket.is_versioned else None,
            multipart=multipart,
            encryption=encryption,
            kms_key_id=kms_key_id,
            bucket_key_enabled=bucket_key_enabled,
        )

        keys = [
            key
            for key in bucket.keys.getlist(key_name, [])
            if key.version_id != new_key.version_id
        ] + [new_key]
        bucket.keys.setlist(key_name, keys)

        return new_key

    def append_to_key(self, bucket_name, key_name, value):
        key_name = clean_key_name(key_name)

        key = self.get_object(bucket_name, key_name)
        key.append_to_value(value)
        return key

    def get_object(self, bucket_name, key_name, version_id=None, part_number=None):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)
        key = None

        if bucket:
            if version_id is None:
                if key_name in bucket.keys:
                    key = bucket.keys[key_name]
            else:
                for key_version in bucket.keys.getlist(key_name, default=[]):
                    if str(key_version.version_id) == str(version_id):
                        key = key_version
                        break

            if part_number and key and key.multipart:
                key = key.multipart.parts[part_number]

        if isinstance(key, FakeKey):
            return key
        else:
            return None

    def get_key_tags(self, key):
        return self.tagger.list_tags_for_resource(key.arn)

    def set_key_tags(self, key, tags, key_name=None):
        if key is None:
            raise MissingKey(key_name)
        self.tagger.delete_all_tags_for_resource(key.arn)
        self.tagger.tag_resource(
            key.arn, [{"Key": k, "Value": v} for (k, v) in tags.items()],
        )
        return key

    def get_bucket_tagging(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return self.tagger.list_tags_for_resource(bucket.arn)

    def put_bucket_tagging(self, bucket_name, tags):
        bucket = self.get_bucket(bucket_name)
        self.tagger.delete_all_tags_for_resource(bucket.arn)
        self.tagger.tag_resource(
            bucket.arn, [{"Key": key, "Value": value} for key, value in tags.items()],
        )

    def delete_bucket_tagging(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        self.tagger.delete_all_tags_for_resource(bucket.arn)

    def put_bucket_cors(self, bucket_name, cors_rules):
        bucket = self.get_bucket(bucket_name)
        bucket.set_cors(cors_rules)

    def put_bucket_logging(self, bucket_name, logging_config):
        bucket = self.get_bucket(bucket_name)
        bucket.set_logging(logging_config, self)

    def delete_bucket_cors(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        bucket.delete_cors()

    def delete_bucket_public_access_block(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        bucket.public_access_block = None

    def delete_account_public_access_block(self, account_id):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        self.account_public_access_block = None

    def put_bucket_notification_configuration(self, bucket_name, notification_config):
        bucket = self.get_bucket(bucket_name)
        bucket.set_notification_configuration(notification_config)

    def put_bucket_accelerate_configuration(
        self, bucket_name, accelerate_configuration
    ):
        if accelerate_configuration not in ["Enabled", "Suspended"]:
            raise MalformedXML()

        bucket = self.get_bucket(bucket_name)
        if bucket.name.find(".") != -1:
            raise InvalidRequest("PutBucketAccelerateConfiguration")
        bucket.set_accelerate_configuration(accelerate_configuration)

    def put_bucket_public_access_block(self, bucket_name, pub_block_config):
        bucket = self.get_bucket(bucket_name)

        if not pub_block_config:
            raise InvalidPublicAccessBlockConfiguration()

        bucket.public_access_block = PublicAccessBlock(
            pub_block_config.get("BlockPublicAcls"),
            pub_block_config.get("IgnorePublicAcls"),
            pub_block_config.get("BlockPublicPolicy"),
            pub_block_config.get("RestrictPublicBuckets"),
        )

    def put_account_public_access_block(self, account_id, pub_block_config):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        if not pub_block_config:
            raise InvalidPublicAccessBlockConfiguration()

        self.account_public_access_block = PublicAccessBlock(
            pub_block_config.get("BlockPublicAcls"),
            pub_block_config.get("IgnorePublicAcls"),
            pub_block_config.get("BlockPublicPolicy"),
            pub_block_config.get("RestrictPublicBuckets"),
        )

    def initiate_multipart(self, bucket_name, key_name, metadata):
        bucket = self.get_bucket(bucket_name)
        new_multipart = FakeMultipart(key_name, metadata)
        bucket.multiparts[new_multipart.id] = new_multipart

        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id, body):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        value, etag = multipart.complete(body)
        if value is None:
            return
        del bucket.multiparts[multipart_id]

        key = self.set_object(
            bucket_name, multipart.key_name, value, etag=etag, multipart=multipart
        )
        key.set_metadata(multipart.metadata)
        return key

    def cancel_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        multipart_data = bucket.multiparts.get(multipart_id, None)
        if not multipart_data:
            raise NoSuchUpload()
        del bucket.multiparts[multipart_id]

    def list_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        return list(bucket.multiparts[multipart_id].list_parts())

    def get_all_multiparts(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.multiparts

    def set_part(self, bucket_name, multipart_id, part_id, value):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, value)

    def copy_part(
        self,
        dest_bucket_name,
        multipart_id,
        part_id,
        src_bucket_name,
        src_key_name,
        src_version_id,
        start_byte,
        end_byte,
    ):
        dest_bucket = self.get_bucket(dest_bucket_name)
        multipart = dest_bucket.multiparts[multipart_id]

        src_value = self.get_object(
            src_bucket_name, src_key_name, version_id=src_version_id
        ).value
        if start_byte is not None:
            src_value = src_value[start_byte : end_byte + 1]
        return multipart.set_part(part_id, src_value)

    def prefix_query(self, bucket, prefix, delimiter):
        key_results = set()
        folder_results = set()
        if prefix:
            for key_name, key in bucket.keys.items():
                if key_name.startswith(prefix):
                    key_without_prefix = key_name.replace(prefix, "", 1)
                    if delimiter and delimiter in key_without_prefix:
                        # If delimiter, we need to split out folder_results
                        key_without_delimiter = key_without_prefix.split(delimiter)[0]
                        folder_results.add(
                            "{0}{1}{2}".format(prefix, key_without_delimiter, delimiter)
                        )
                    else:
                        key_results.add(key)
        else:
            for key_name, key in bucket.keys.items():
                if delimiter and delimiter in key_name:
                    # If delimiter, we need to split out folder_results
                    folder_results.add(key_name.split(delimiter)[0] + delimiter)
                else:
                    key_results.add(key)

        key_results = filter(
            lambda key: not isinstance(key, FakeDeleteMarker), key_results
        )
        key_results = sorted(key_results, key=lambda key: key.name)
        folder_results = [
            folder_name for folder_name in sorted(folder_results, key=lambda key: key)
        ]

        return key_results, folder_results

    def _set_delete_marker(self, bucket_name, key_name):
        bucket = self.get_bucket(bucket_name)
        delete_marker = FakeDeleteMarker(key=bucket.keys[key_name])
        bucket.keys[key_name] = delete_marker
        return delete_marker

    def delete_object_tagging(self, bucket_name, key_name, version_id=None):
        key = self.get_object(bucket_name, key_name, version_id=version_id)
        self.tagger.delete_all_tags_for_resource(key.arn)

    def delete_object(self, bucket_name, key_name, version_id=None):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)

        response_meta = {}

        try:
            if not bucket.is_versioned:
                bucket.keys.pop(key_name)
            else:
                if version_id is None:
                    delete_marker = self._set_delete_marker(bucket_name, key_name)
                    response_meta["version-id"] = delete_marker.version_id
                else:
                    if key_name not in bucket.keys:
                        raise KeyError

                    response_meta["delete-marker"] = "false"
                    for key in bucket.keys.getlist(key_name):
                        if str(key.version_id) == str(version_id):
                            if type(key) is FakeDeleteMarker:
                                response_meta["delete-marker"] = "true"
                            break

                    bucket.keys.setlist(
                        key_name,
                        [
                            key
                            for key in bucket.keys.getlist(key_name)
                            if str(key.version_id) != str(version_id)
                        ],
                    )

                    if not bucket.keys.getlist(key_name):
                        bucket.keys.pop(key_name)
            return True, response_meta
        except KeyError:
            return False, None

    def copy_key(
        self,
        src_bucket_name,
        src_key_name,
        dest_bucket_name,
        dest_key_name,
        storage=None,
        acl=None,
        src_version_id=None,
    ):
        src_key_name = clean_key_name(src_key_name)
        dest_key_name = clean_key_name(dest_key_name)
        dest_bucket = self.get_bucket(dest_bucket_name)
        key = self.get_object(src_bucket_name, src_key_name, version_id=src_version_id)

        new_key = key.copy(dest_key_name, dest_bucket.is_versioned)
        self.tagger.copy_tags(key.arn, new_key.arn)

        if storage is not None:
            new_key.set_storage_class(storage)
        if acl is not None:
            new_key.set_acl(acl)
        if key.storage_class in "GLACIER":
            # Object copied from Glacier object should not have expiry
            new_key.set_expiry(None)

        dest_bucket.keys[dest_key_name] = new_key

    def set_bucket_acl(self, bucket_name, acl):
        bucket = self.get_bucket(bucket_name)
        bucket.set_acl(acl)

    def get_bucket_acl(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.acl

    def get_bucket_cors(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.cors

    def get_bucket_logging(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.logging

    def get_bucket_notification_configuration(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.notification_configuration


s3_backend = S3Backend()
