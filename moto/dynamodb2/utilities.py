def is_int(val):
    if type(val) == int:
        return True
    try:
        int(val)
        return True
    except ValueError:
        return False


def is_float(val):
    if type(val) == float:
        return True
    try:
        float(val)
        return True
    except ValueError:
        return False
