from datetime import datetime, timedelta

from moto.core.utils import utcnow


def pytest_parametrize_test_create_get_schedule__with_start_date() -> list[datetime]:
    now = utcnow()
    timedelta_kwargs = {"days": 1, "hours": 1, "weeks": 1}
    return_ = []
    for k, v in timedelta_kwargs.items():
        return_.append(now + timedelta(**{k: v}))
    else:
        return_.append(now.replace(year=now.year + 1))
    return return_


def pytest_parametrize_test_create_schedule__exception_with_start_date() -> list[
    datetime
]:
    now = utcnow()
    timedelta_kwargs = {"days": 1, "minutes": 6, "hours": 1, "weeks": 1}
    return_ = []
    for k, v in timedelta_kwargs.items():
        return_.append(now - timedelta(**{k: v}))
    else:
        return_.append(now.replace(year=now.year - 1))
    return return_
