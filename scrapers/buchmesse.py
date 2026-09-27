"""Frankfurter Buchmesse – dates from the official homepage ('7 – 11 October 2026')."""
from .base import seasonal

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "buchmesse", "name": "Frankfurter Buchmesse", "url": "https://www.buchmesse.de/en"}


def scrape(ctx):
    return seasonal(ctx, SOURCE, "Frankfurter Buchmesse", "Messe Frankfurt", "Frankfurt",
                    "Ludwig-Erhard-Anlage 1, 60327 Frankfurt am Main")
