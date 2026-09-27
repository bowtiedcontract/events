"""Städel Museum – exhibition list; titles sit above a date-range line."""
from .base import exhibitions

SOURCE = {"id": "staedel", "name": "Städel Museum", "url": "https://www.staedelmuseum.de/de/ausstellungen-programm"}


def scrape(ctx):
    return exhibitions(ctx, SOURCE["url"], "Städel Museum", title_offset=2)
