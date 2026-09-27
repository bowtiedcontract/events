"""Kunsthalle Mainz – exhibition list; titles sit above a date-range line."""
from .base import exhibitions

SOURCE = {"id": "kunsthalle_mainz", "name": "Kunsthalle Mainz", "url": "https://www.kunsthalle-mainz.de/"}


def scrape(ctx):
    return exhibitions(ctx, SOURCE["url"], "Kunsthalle Mainz", title_offset=1)
