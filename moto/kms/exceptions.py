from moto.core.exceptions import RESTError


class InvalidKeyUsageError(RESTError):
    def __init__(self, key_spec):
        self.code = 400
        super(InvalidKeyUsageError, self).__init__(
            'InvalidKeyUsageError', "Value '{}' at 'keySpec' failed to satisfy constraint: Member "
                                    "must satisfy enum value set: "
                                    "[AES_256, AES_128]".format(key_spec))
