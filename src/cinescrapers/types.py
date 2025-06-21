import datetime


from pydantic import BaseModel


class ShowTime(BaseModel):
    cinema: str
    title: str
    link: str
    datetime: datetime.datetime
    description: str
    image_src: str | None


class EnrichedShowTime(ShowTime):
    last_updated: datetime.datetime
    scraper: str
