import boto.beanstalk

from moto.core import BaseBackend, BaseModel
from .exceptions import InvalidParameterValueError


class FakeApplication(BaseModel):
    def __init__(self, application_name):
        self.application_name = application_name


class EBBackend(BaseBackend):
    def __init__(self, region):
        self.region = region
        self.applications = dict()

    def reset(self):
        # preserve region
        region = self.region
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region)

    def create_application(self, application_name):
        if application_name in self.applications:
            raise InvalidParameterValueError(
                "Application {} already exists.".format(application_name)
            )
        new_app = FakeApplication(
            application_name=application_name,
        )
        self.applications[application_name] = new_app
        return new_app


eb_backends = dict((region.name, EBBackend(region.name))
                   for region in boto.beanstalk.regions())
