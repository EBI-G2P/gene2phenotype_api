#!/usr/bin/env python3

from datetime import datetime
import pytz

def get_date_now():
    timezone = pytz.timezone("Europe/London")
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_obj = datetime.strptime(date_now, '%Y-%m-%d %H:%M:%S')
    aware_datetime = timezone.localize(date_obj)

    return aware_datetime
