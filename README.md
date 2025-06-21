# CineScrapers

Tools for scraping cinema websites, in an effort to eventually create unified
listings data. For now, I'm targetting the handful of independent cinemas
in London that are on my radar.

There's a lot to do just to get that far and frankly I'm not especially expert
at web scraping, so if you're able to contribute it'd be much appreciated!

The roadmap is to keep working on the scrapers, and once there's enough data
for it to be worthwhile I'll publish it, both in human-friendly and
machine-readable formats.

## Done

* Prince Charles Cinema
* Close-Up Film Centre

## TODO

* Barbican Cinemas
* Kiln Theatre
* Arthouse Crouch End
* BFI IMAX
* BFI Southbank
* The Arzner
* The Castle Cinema
* The Lumiere Romford
* The ICA
* The Rio (Dalston)

## Usage

* Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
* `cd src/`
* `uv run python -m cinescrapers prince_charles_cinema`, to scrape the PCC website's listings
  into an sqlite file (`showtimes.db`)
* `uv run python -m cinescrapers` to see a list of scrapers (all two of them).
