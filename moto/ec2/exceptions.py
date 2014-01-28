class InvalidIdError(RuntimeError):
    def __init__(self, id_value):
        super(InvalidIdError, self).__init__()
        self.id = id_value
