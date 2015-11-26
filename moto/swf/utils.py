from datetime import datetime
from time import mktime


def decapitalize(key):
    return key[0].lower() + key[1:]

def now_timestamp():
    return float(mktime(datetime.utcnow().timetuple()))
