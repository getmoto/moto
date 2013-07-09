class InvalidIdError(RuntimeError):
    def __init__(self, instance_id):
        super(InvalidIdError, self).__init__()
        self.instance_id = instance_id
