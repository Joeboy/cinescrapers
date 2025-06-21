from typing import TypedDict


class DateTimeStr(str):
    pass


class ShowTime(TypedDict):
    cinema: str
    title: str
    link: str
    datetime: DateTimeStr
    description: str
    image_src: str | None
