import datetime

from pydantic import BaseModel, Field, computed_field

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
    release_year: int | None = None
    imdb_id: str | None = Field(min_length=1, default=None)


class EnrichedShowTime(ShowTime):
    """Showtime data that has been enriched with additional information."""

    id: str
    last_updated: datetime.datetime
    scraper: str
    norm_title: str  # Normalized title for matching / sorting
    thumbnail: str | None
    tmdb_id: int | None = None  # TMDB ID for the film, if available


class TmdbItemFeatures(BaseModel):
    """TMDB item features that can be used to match showtimes with TMDB IDs."""

    tmdb_id: int
    overview_embed_similarity: float
    overview_tf_similarity: float
    image_embed_similarity: float
    is_recent: bool
    vote_count: int

    def get_score(self) -> float:
        """Ghetto calculation of an overall score based on various features"""
        if self.overview_embed_similarity > 0.2:
            overview_embed_similarity_points = (
                (self.overview_embed_similarity - 0.2) * 1.0 / 0.8
            )
        else:
            overview_embed_similarity_points = 0.0
        print(
            f"Adding {overview_embed_similarity_points} points for overview similarity"
        )

        # increase points if image is similar to the showtime image:
        if self.image_embed_similarity > 0.65:
            image_embed_similarity_points = (
                (self.image_embed_similarity - 0.65) * 1.0 / 0.35
            )
        else:
            image_embed_similarity_points = 0.0
        print(f"Adding {image_embed_similarity_points} points for image similarity")
        vote_count_points = 0.1 * (self.vote_count > 100)
        print(f"Adding {vote_count_points} points for vote count")
        return (
            overview_embed_similarity_points
            + image_embed_similarity_points
            + self.is_recent * 0.1
            + vote_count_points
        )
