import zoneinfo
from datetime import datetime

# Define Beijing's timezone
cn_timezone = zoneinfo.ZoneInfo("Asia/Shanghai")


def cn_now():
    return datetime.now(tz=cn_timezone)


def get_current_date():
    return cn_now().date().strftime("%Y-%m-%d")


def get_current_datetime():
    return cn_now().strftime("%Y-%m-%d_%H_%M_%S")
