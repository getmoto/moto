from moto.core.responses import BaseResponse
from ..utils import convert_tag_spec


class EC2BaseResponse(BaseResponse):
    def _filters_from_querystring(self):
        # [{"Name": x1, "Value": y1}, ..]
        _filters = self._get_multi_param("Filter.")
        # return {x1: y1, ...}
        return {f["Name"]: f["Value"] for f in _filters}

    def _parse_tag_specification(self):
        # [{"ResourceType": _type, "Tag": [{"Key": k, "Value": v}, ..]}]
        tag_spec_set = self._get_multi_param("TagSpecification")
        # {_type: {k: v, ..}}
        return convert_tag_spec(tag_spec_set)
