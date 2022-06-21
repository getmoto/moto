from moto.core.exceptions import JsonRESTError

""" will need exceptions for each api endpoint hit """

class InvalidInputException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidInputException", message)