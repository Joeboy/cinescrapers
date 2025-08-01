import datetime

from pydantic import BaseModel, computed_field

from .utils import extract_uk_postcode


class Cinema(BaseModel):
    shortcode: str
    shortname: str
    name: str
    url: str
    address: str
    phone: str | None
    latitude: float
    longitude: float

    @computed_field
    @property
    def postcode(self) -> str | None:
        """Auto-generated postcode extracted from the address. Let's assume
        every address has a postcode in it."""

        return extract_uk_postcode(self.address)


class ShowTime(BaseModel):
    """Showtime data that will be scraped from cinema websites."""
    cinema_shortcode: str
    title: str
    link: str
    datetime: datetime.datetime
    description: str
    image_src: str | None


class EnrichedShowTime(ShowTime):
    """Showtime data that has been enriched with additional information."""
    id: str
    last_updated: datetime.datetime
    scraper: str
    norm_title: str  # Normalized title for matching / sorting
    thumbnail: str | None
    tmdb_id: int | None = None  # TMDB ID for the film, if available
