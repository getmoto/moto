import json

from moto.core.responses import BaseResponse
from . import meteringmarketplace_backends
from .models import Result


class MarketplaceMeteringResponse(BaseResponse):
    @property
    def _product(self):
        return self.body["ProductCode"]

    @property
    def marketplacemetering_backend(self):
        return meteringmarketplace_backends[self.region]

    @property
    def product_records(self):
        return self.marketplacemetering_backend.records_by_product[self._product]

    @property
    def product_customers(self):
        return self.marketplacemetering_backend.customers_by_product[self._product]

    def batch_meter_usage(self):
        records = self.product_records
        customers = self.product_customers
        results = []
        for usage in self.body["UsageRecords"]:
            result = Result(**usage)
            if not customers.is_subscribed(result.usage_record.customer_identifier):
                # TODO: can I check for this? How do you subscribe?
                result.status = result.CUSTOMER_NOT_SUBSCRIBED
            elif records.is_duplicate(result):
                result.status = result.DUPLICATE_RECORD
            else:
                records.append(result)
            results.append(result)
        return 200, {}, json.dumps({"Results": results,  "UnprocessedRecords": []})
