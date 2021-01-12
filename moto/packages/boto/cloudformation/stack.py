class Output(object):
    def __init__(self, connection=None):
        self.connection = connection
        self.description = None
        self.key = None
        self.value = None

    def __repr__(self):
        return 'Output:"%s"="%s"' % (self.key, self.value)
