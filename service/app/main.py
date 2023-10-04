from enum import Enum
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, root_validator


app = FastAPI()


class DayOfWeek(Enum):
    Sunday = "Sunday"
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"


class DateOrDay(BaseModel):
    date: Optional[str]
    day: Optional[DayOfWeek]

    @root_validator(pre=True)
    def check_only_one_exists(cls, values):
        assert (
            "date" in values.keys() or "day" in values.keys()
        ), "Specific either `date` or `day` but not both"
        assert not (
            "date" in values.keys() and "day" in values.keys()
        ), "Specific either `date` or `day` but not both"
        if "date" in values:
            date = values["date"].split("/")
            assert len(date) == 3
        return values


@app.get("/")
async def list_endpoints():
    return {
        "Available endpoints": [
            "GET /",
            "GET /greeting",
            "GET /greeting/{name}",
            "POST /greeting_with_date_or_day",
        ]
    }


@app.get("/greeting")
async def greeting():
    return "Hello, welcome to my endpoint!"


@app.get("/greeting/name")  # query parameter
async def greeting_name_query(name: str):
    return f"Hello {name}, welcome to my endpoint!"


@app.get("/greeting/{name}")  # path parameter
async def greeting_name_path(name: str):
    return f"Hello {name}, welcome to my endpoint!"


@app.post("/greeting_with_date_or_day")
async def greeting_with_date_or_day(date_or_day: DateOrDay):  # request body
    if date_or_day.date:
        return f"Hello, the date is {date_or_day.date}. Welcome to my endpoint!"
    else:
        return f"Hello, the day is {date_or_day.day.value}. Welcome to my endpoint!"