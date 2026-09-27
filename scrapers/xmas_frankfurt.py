"""Frankfurter Weihnachtsmarkt – dates from visitfrankfurt ('23.11. – 22.12.2026')."""
from .base import seasonal

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "xmas_frankfurt", "name": "Frankfurter Weihnachtsmarkt",
          "url": "https://www.visitfrankfurt.travel/erleben/feste-und-veranstaltungen/frankfurter-weihnachtsmarkt"}


def scrape(ctx):
    return seasonal(ctx, SOURCE, "Frankfurter Weihnachtsmarkt", "Römerberg & Innenstadt", "Frankfurt",
                    "Römerberg, 60311 Frankfurt am Main", near=r"Weihnachtsmarkt")
