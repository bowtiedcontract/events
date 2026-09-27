"""Museum Wiesbaden – exhibition list; titles sit above a date-range line."""
from .base import exhibitions

SOURCE = {"id": "museum_wiesbaden", "name": "Museum Wiesbaden", "url": "https://museum-wiesbaden.de/ausstellungen"}


def scrape(ctx):
    return exhibitions(ctx, SOURCE["url"], "Museum Wiesbaden", title_offset=2)
