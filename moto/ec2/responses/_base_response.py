from moto.core.responses import BaseResponse


class EC2BaseResponse(BaseResponse):
    def _filters_from_querystring(self):
        # [{"Name": x1, "Value": y1}, ..]
        _filters = self._get_multi_param("Filter.")
        # return {x1: y1, ...}
        return {f["Name"]: f["Value"] for f in _filters}
