from moto.core import BaseModel
from moto.core.utils import camelcase_to_underscores


class GenericType(BaseModel):
    def __init__(self, name, version, **kwargs):
        self.name = name
        self.version = version
        self.status = "REGISTERED"
        if "description" in kwargs:
            self.description = kwargs.pop("description")
        for key, value in kwargs.items():
            self.__setattr__(key, value)
        # default values set to none
        for key in self._configuration_keys:
            attr = camelcase_to_underscores(key)
            if not hasattr(self, attr):
                self.__setattr__(attr, None)
        if not hasattr(self, "task_list"):
            self.task_list = None

    def __repr__(self):
        cls = self.__class__.__name__
        attrs = (
            "name: %(name)s, version: %(version)s, status: %(status)s" % self.__dict__
        )
        return "{0}({1})".format(cls, attrs)

    @property
    def kind(self):
        raise NotImplementedError()

    @property
    def _configuration_keys(self):
        raise NotImplementedError()

    def to_short_dict(self):
        return {"name": self.name, "version": self.version}

    def to_medium_dict(self):
        hsh = {
            "{0}Type".format(self.kind): self.to_short_dict(),
            "creationDate": 1420066800,
            "status": self.status,
        }
        if self.status == "DEPRECATED":
            hsh["deprecationDate"] = 1422745200
        if hasattr(self, "description"):
            hsh["description"] = self.description
        return hsh

    def to_full_dict(self):
        hsh = {"typeInfo": self.to_medium_dict(), "configuration": {}}
        if self.task_list:
            hsh["configuration"]["defaultTaskList"] = {"name": self.task_list}
        for key in self._configuration_keys:
            attr = camelcase_to_underscores(key)
            if not getattr(self, attr):
                continue
            hsh["configuration"][key] = getattr(self, attr)
        return hsh
