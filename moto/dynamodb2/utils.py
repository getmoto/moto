from __future__ import unicode_literals
import calendar


def unix_time(dt):
    return calendar.timegm(dt.timetuple())
