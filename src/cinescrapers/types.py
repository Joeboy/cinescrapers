import datetime


from pydantic import BaseModel


class Cinema(BaseModel):
    shortcode: str
    shortname: str
    name: str
    url: str
    address: str | None
    phone: str | None
    latitude: float
    longitude: float


class ShowTime(BaseModel):
    cinema_shortcode: str
    title: str
    link: str
    datetime: datetime.datetime
    description: str
    image_src: str | None


class EnrichedShowTime(ShowTime):
    id: str
    last_updated: datetime.datetime
    scraper: str
    thumbnail: str | None
