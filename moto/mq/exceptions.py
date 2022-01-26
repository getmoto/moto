import json
from moto.core.exceptions import JsonRESTError


class MQError(JsonRESTError):
    pass


class UnknownBroker(MQError):
    def __init__(self, broker_id):
        super().__init__("NotFoundException", "Can't find requested broker")
        self.broker_id = broker_id

    def get_body(self):
        body = {
            "errorAttribute": "broker-id",
            "message": f"Can't find requested broker [{self.broker_id}]. Make sure your broker exists.",
        }
        return json.dumps(body)


class UnknownConfiguration(MQError):
    def __init__(self, config_id):
        super().__init__("NotFoundException", "Can't find requested configuration")
        self.config_id = config_id

    def get_body(self):
        body = {
            "errorAttribute": "configuration_id",
            "message": f"Can't find requested configuration [{self.config_id}]. Make sure your configuration exists.",
        }
        return json.dumps(body)


class UnknownUser(MQError):
    def __init__(self, username):
        super().__init__("NotFoundException", "Can't find requested user")
        self.username = username

    def get_body(self):
        body = {
            "errorAttribute": "username",
            "message": f"Can't find requested user [{self.username}]. Make sure your user exists.",
        }
        return json.dumps(body)


class UnsupportedEngineType(MQError):
    def __init__(self, engine_type):
        super().__init__("BadRequestException", "")
        self.engine_type = engine_type

    def get_body(self):
        body = {
            "errorAttribute": "engineType",
            "message": f"Broker engine type [{self.engine_type}] does not support configuration.",
        }
        return json.dumps(body)


class UnknownEngineType(MQError):
    def __init__(self, engine_type):
        super().__init__("BadRequestException", "")
        self.engine_type = engine_type

    def get_body(self):
        body = {
            "errorAttribute": "engineType",
            "message": f"Broker engine type [{self.engine_type}] is invalid. Valid values are: [ACTIVEMQ]",
        }
        return json.dumps(body)
