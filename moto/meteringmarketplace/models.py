import collections
from moto.core import BaseBackend, BaseModel
from moto.moto_api._internal import mock_random
from moto.core.utils import BackendDict


class UsageRecord(BaseModel, dict):
    def __init__(self, timestamp, customer_identifier, dimension, quantity=0):
        super().__init__()
        self.timestamp = timestamp
        self.customer_identifier = customer_identifier
        self.dimension = dimension
        self.quantity = quantity
        self.metering_record_id = mock_random.uuid4().hex

    @classmethod
    def from_data(cls, data):
        cls(
            timestamp=data.get("Timestamp"),
            customer_identifier=data.get("CustomerIdentifier"),
            dimension=data.get("Dimension"),
            quantity=data.get("Quantity", 0),
        )

    @property
    def timestamp(self):
        return self["Timestamp"]

    @timestamp.setter
    def timestamp(self, value):
        self["Timestamp"] = value

    @property
    def customer_identifier(self):
        return self["CustomerIdentifier"]

    @customer_identifier.setter
    def customer_identifier(self, value):
        self["CustomerIdentifier"] = value

    @property
    def dimension(self):
        return self["Dimension"]

    @dimension.setter
    def dimension(self, value):
        self["Dimension"] = value

    @property
    def quantity(self):
        return self["Quantity"]

    @quantity.setter
    def quantity(self, value):
        self["Quantity"] = value


class Result(BaseModel, dict):
    SUCCESS = "Success"
    CUSTOMER_NOT_SUBSCRIBED = "CustomerNotSubscribed"
    DUPLICATE_RECORD = "DuplicateRecord"

    def __init__(self, **kwargs):
        self.usage_record = UsageRecord(
            timestamp=kwargs["Timestamp"],
            customer_identifier=kwargs["CustomerIdentifier"],
            dimension=kwargs["Dimension"],
            quantity=kwargs["Quantity"],
        )
        self.status = Result.SUCCESS
        self["MeteringRecordId"] = self.usage_record.metering_record_id

    @property
    def metering_record_id(self):
        return self["MeteringRecordId"]

    @property
    def status(self):
        return self["Status"]

    @status.setter
    def status(self, value):
        self["Status"] = value

    @property
    def usage_record(self):
        return self["UsageRecord"]

    @usage_record.setter
    def usage_record(self, value):
        if not isinstance(value, UsageRecord):
            value = UsageRecord.from_data(value)
        self["UsageRecord"] = value

    def is_duplicate(self, other):
        """
        DuplicateRecord - Indicates that the UsageRecord was invalid and not honored.
        A previously metered UsageRecord had the same customer, dimension, and time,
        but a different quantity.
        """
        assert isinstance(other, Result), "Needs to be a Result type"
        usage_record, other = other.usage_record, self.usage_record
        return (
            other.customer_identifier == usage_record.customer_identifier
            and other.dimension == usage_record.dimension
            and other.timestamp == usage_record.timestamp
            and other.quantity != usage_record.quantity
        )


class CustomerDeque(collections.deque):
    def is_subscribed(self, customer):
        return customer in self


class ResultDeque(collections.deque):
    def is_duplicate(self, result):
        return any(record.is_duplicate(result) for record in self)


class MeteringMarketplaceBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.customers_by_product = collections.defaultdict(CustomerDeque)
        self.records_by_product = collections.defaultdict(ResultDeque)

    def batch_meter_usage(self, product_code, usage_records):
        results = []
        for usage in usage_records:
            result = Result(**usage)
            if not self.customers_by_product[product_code].is_subscribed(
                result.usage_record.customer_identifier
            ):
                result.status = result.CUSTOMER_NOT_SUBSCRIBED
            elif self.records_by_product[product_code].is_duplicate(result):
                result.status = result.DUPLICATE_RECORD
            results.append(result)
        return results


meteringmarketplace_backends = BackendDict(
    MeteringMarketplaceBackend, "meteringmarketplace"
)
