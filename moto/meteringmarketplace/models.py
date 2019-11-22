from boto3.session import Session

from moto.core import BaseBackend, BaseModel


class UsageRecord(BaseModel, dict):
    def __init__(self, timestamp, customer_identifier, dimension, quantity=0):
        super(UsageRecord, self).__init__()
        self["Timestamp"] = timestamp
        self["CustomerIdentifier"] = customer_identifier
        self["Dimension"] = dimension
        self["Quantity"] = quantity

    @classmethod
    def from_data(cls, data):
        cls(
            timestamp=data.get("Timestamp"),
            customer_identifier=data.get("CustomerIdentifier"),
            dimension=data.get("Dimension"),
            quantity=data.get("Quantity", 0),
        )


class MeteringMarketplaceBackend(BaseBackend):
    def __init__(self, region_name):
        super(MeteringMarketplaceBackend, self).__init__()
        self.region_name = region_name
        self.product_codes = set()
        self.meter_usages = {}


meteringmarketplace_backends = {}
for region_name in Session().get_available_regions("meteringmarketplace"):
    meteringmarketplace_backends[region_name] = MeteringMarketplaceBackend(region_name)
