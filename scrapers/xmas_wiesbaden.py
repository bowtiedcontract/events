"""Wiesbaden Sternschnuppenmarkt – dates from tourismus.wiesbaden.de ('vom 24. November bis 23. Dezember 2026')."""
from .base import seasonal

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "xmas_wiesbaden", "name": "Sternschnuppenmarkt Wiesbaden",
          "url": "https://tourismus.wiesbaden.de/erleben/events/stadtevents/sternschnuppenmarkt"}


def scrape(ctx):
    return seasonal(ctx, SOURCE, "Sternschnuppenmarkt", "Schlossplatz / Marktkirche", "Wiesbaden",
                    "Schlossplatz, 65183 Wiesbaden", near=r"verwandelt sich|vom \d")
