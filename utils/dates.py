from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

CSS_CLASSES = {True: "day day-full", False: "day ", None: "day day-disabled"}


def parse_date(date):
    if not date:
        return datetime.now()
    month, year = date.split("-")
    return datetime(int(year), int(month), 1)


def get_month_grid(date, db_dates):
    today = datetime.now()
    today = datetime(today.year, today.month, today.day)
    db_dates = [datetime(d.year, d.month, d.day) for d in db_dates]
    year, month = date.year, date.month
    first_day_month = datetime(year, month, 1)
    init_grid = first_day_month - timedelta(days=first_day_month.weekday())
    grid = [[init_grid + timedelta(days=i * 7 + j) for j in range(7)] for i in range(6)]
    if not [d for d in grid[-1] if d.month == month]:
        grid = grid[:-1]
    dates = {d: d in db_dates if d.month == month else None for w in grid for d in w}
    return {
        d: CSS_CLASSES.get(val) + (" today" if val is not None and d == today else "")
        for d, val in dates.items()
    }


def get_adj_months(date):
    prev_month = date - relativedelta(months=1)
    next_month = date + relativedelta(months=1)
    return format(prev_month, "%m-%Y"), format(next_month, "%m-%Y")
