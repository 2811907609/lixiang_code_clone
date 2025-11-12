from datetime import datetime

from sysutils.xdatetime import get_current_date, get_current_datetime


def test_get_current_date():
    # 验证日期格式为 YYYY-MM-DD
    date_str = get_current_date()
    assert len(date_str) == 10
    assert date_str.count("-") == 2
    # 验证日期是否有效
    datetime.strptime(date_str, "%Y-%m-%d")


def test_get_current_datetime():
    # 验证日期时间格式为 YYYY-MM-DD_HH:MM:SS
    datetime_str = get_current_datetime()
    assert len(datetime_str) == 19
    assert datetime_str.count("-") == 2
    assert datetime_str.count("_") == 3
    # 验证日期时间是否有效
    datetime.strptime(datetime_str, "%Y-%m-%d_%H_%M_%S")
