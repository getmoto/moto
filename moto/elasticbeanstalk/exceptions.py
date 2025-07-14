from moto.core.exceptions import ServiceException


class ElasticBeanstalkException(ServiceException):
    pass


class InvalidParameterValueError(ServiceException):
    def __init__(self, message: str):
        super().__init__("InvalidParameterValue", message)


class ResourceNotFoundException(ServiceException):
    def __init__(self, message: str):
        super().__init__("ResourceNotFoundException", message)


class ApplicationNotFound(ElasticBeanstalkException):
    def __init__(self, application_name: str):
        super().__init__(
            "ApplicationNotFound",
            message=f"Elastic Beanstalk application {application_name} not found.",
        )
