class ScrapingError(Exception):
    pass


class TooManyRequestsError(Exception):
    """RapidAPI only allows us a tiny no. of requests with the free plan :-("""

    pass

class EmptyPage(Exception):
    """We got an empty page (which probably means we ran out of pages while
    hitting an API)"""