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

* ActOne
* Arthouse Crouch End
* Barbican Cinemas
* Bertha Dochouse
* BFI Southbank
* The Arzner
* The Castle Cinema
* Chiswick Cinema
* Cine Lumiere
* Close-Up Film Centre
* Coldharbour Blue
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
* Electric Cinema Portobello
* Electric Cinema White City

## TODO

* BFI IMAX
* The Nickel
* Ciné Reel
* David Lean Cinema
* Cinema Museum, Kenninton
* Theatreship, Canary Wharf
* Sands Films

## Usage

* Make sure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
* `cd src/`
* `uv run python -m cinescrapers scrape ica`, to run the `ica` scraper, which will
  scrape the ICA website's film listings into an sqlite file (`showtimes.db`)
* `uv run python -m cinescrapers list-scrapers` to see the list of scrapers.
