def is_integer_between(x, mn=None, mx=None, optional=False):
    if optional and x is None:
        return True
    try:
        if mn is not None and mx is not None:
            return int(x) >= mn and int(x) < mx
        elif mn is not None:
            return int(x) >= mn
        elif mx is not None:
            return int(x) < mx
        else:
            return True
    except ValueError:
        return False


def is_one_of(x, choices, optional=False):
    if optional and x is None:
        return True
    return x in choices
