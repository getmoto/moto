from typing import List, Tuple

from moto.core.exceptions import JsonRESTError


class Route53DomainsValidationException(JsonRESTError):
    code = 400

    def __init__(self, error_tuples: List[Tuple[str, str, str]]):
        """Validation errors are concatenated into one exception message.

        error_tuples is a list of tuples.  Each tuple contains:

          - name of invalid parameter,
          - value of invalid parameter,
          - string describing the constraints for that parameter.
        """
        msg_leader = (
            f'{len(error_tuples)} '
            f'validation error{'s' if len(error_tuples) > 1 else ''} detected: '
        )
        msgs = []
        for arg_name, arg_value, constraint in error_tuples:
            msgs.append(
                f"Value '{arg_value}' at '{arg_name}' failed to satisfy "
                f"constraint: Member must {constraint}"
            )
        super().__init__('ValidationException', msg_leader + '; '.join(msgs))
