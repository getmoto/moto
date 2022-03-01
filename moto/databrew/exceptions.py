from moto.core.exceptions import JsonRESTError


class DataBrewClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(DataBrewClientError):
    def __init__(self, typ):
        super().__init__("AlreadyExistsException", "%s already exists." % (typ))


class RecipeAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Recipe")


class EntityNotFoundException(DataBrewClientError):
    def __init__(self, msg):
        super().__init__("EntityNotFoundException", msg)


class RecipeNotFoundException(EntityNotFoundException):
    def __init__(self, recipe_name):
        super().__init__("Recipe %s not found." % recipe_name)
