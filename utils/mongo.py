from datetime import datetime, timedelta, timezone
from os import getenv

from dateutil.relativedelta import relativedelta
from pymongo import MongoClient

# ---- Database


def init_connection():
    max_idle_time = 3  # minutes
    connection = (
        f"mongodb+srv://{getenv('MONGO_USER')}:{getenv('MONGO_PASSWORD')}"
        f"@{getenv('MONGO_IP')}/?retryWrites=true&w=majority"
        f"&maxIdleTimeMS={max_idle_time * 60000}"
    )
    return MongoClient(connection)


def connect():
    return init_connection()[getenv("MONGO_COLLECTION")]


def save_on_mongo(facts):
    db = connect()
    today = datetime.now()
    data = {"timestamp": today, "year": today.year, "output": facts}
    return db.facts.insert_one(data)


def get_facts_from_mongo(day=None):
    db = connect()
    day = day or format(datetime.now(), "%d-%m-%Y")
    day_utc = datetime(*map(int, day.split("-")[::-1]), tzinfo=timezone.utc)
    filters = {"timestamp": {"$gte": day_utc, "$lt": day_utc + timedelta(days=1)}}
    data = db.facts.find_one(filters, projection={"_id": False, "output": True})
    return data | {"day": day_utc}


def get_facts_dates(date):
    db = connect()
    start_d = datetime(date.year, date.month, 1)
    filters = {"timestamp": {"$gte": start_d, "$lt": start_d + relativedelta(months=1)}}
    projection = {"_id": False, "timestamp": True}
    return [el.get("timestamp") for el in db.facts.find(filters, projection=projection)]
