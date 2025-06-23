# CineScrapers

Tools for scraping cinema websites, in an effort to eventually create unified
listings data. For now, I'm targetting the handful of independent cinemas
in London that are on my radar.

There's a lot to do just to get that far and frankly I'm not especially expert
at web scraping, so if you're able to contribute it'd be much appreciated!
Also if you know how to get any of this info in a more straightforward way (like
a free API), please let me know!

See [https://filmhose.uk] for a website that uses the scraped data.

## Done

(sort of done, anyway, there are very probably bugs)

* Prince Charles Cinema
* Close-Up Film Centre
* BFI Southbank
* The ICA

## TODO

* Barbican Cinemas
* Kiln Theatre
* Arthouse Crouch End
* BFI IMAX
* The Arzner
* The Castle Cinema
* The Lumiere Romford
* The Rio (Dalston)
* The Nickel
* Sands Films

## Usage

* Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
* `cd src/`
* `uv run python -m cinescrapers ica`, to run the `ica` scraper, which will
  scrape the ICA website's film listings into an sqlite file (`showtimes.db`)
* `uv run python -m cinescrapers --list-scrapers` to see the list of scrapers.
