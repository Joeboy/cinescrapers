import datetime


from pydantic import BaseModel


class ShowTime(BaseModel):
    cinema_shortname: str
    cinema_name: str
    title: str
    link: str
    datetime: datetime.datetime
    description: str
    image_src: str | None


class EnrichedShowTime(ShowTime):
    id: str
    last_updated: datetime.datetime
    scraper: str
