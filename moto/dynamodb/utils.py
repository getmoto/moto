import calendar


def unix_time(dt):
    return calendar.timegm(dt.timetuple())
