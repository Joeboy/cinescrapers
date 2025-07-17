# CineScrapers

Tools for scraping cinema websites, in an effort to create unified listings
info. See [filmhose.uk](https://filmhose.uk) for a website that uses the
scraped listings.

There's still a lot to do and frankly I'm not especially expert at web
scraping, so if you're able to contribute it'd be much appreciated! Also if you
know how to get any of this info in a more straightforward way (like a free
API), please let me know!

## Done

(sort of done, anyway, there are very probably bugs)

* Arthouse Crouch End
* Barbican Cinemas
* Bertha Dochouse
* BFI Southbank
* The Arzner
* The Castle Cinema
* Close-Up Film Centre
* Garden Cinema
* The Genesis
* The ICA
* Kiln Theatre
* The Lexi Cinema
* Peckhamplex
* Phoenix Cinema
* Prince Charles Cinema
* Regent Street Cinema
* Rich Mix
* The Rio
* The Romford Lumiere
* Throwley Yard

## TODO

* BFI IMAX
* Cine Lumiere, South Kensington
* The Nickel
* ActOne
* Ciné Reel
* Electric Cinema
* David Lean Cinema
* Chiswick Cinema
* Cinema Museum, Kenninton
* Theatreship, Canary Wharf
* Whirled Cinema
* Sands Films

## Usage

* Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
* `cd src/`
* `uv run python -m cinescrapers scrape ica`, to run the `ica` scraper, which will
  scrape the ICA website's film listings into an sqlite file (`showtimes.db`)
* `uv run python -m cinescrapers list-scrapers` to see the list of scrapers.
