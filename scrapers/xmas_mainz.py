"""Mainzer Weihnachtsmarkt – dates from mainz.de ('vom 26. November bis 23. Dezember 2026')."""
from .base import seasonal

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "xmas_mainz", "name": "Mainzer Weihnachtsmarkt",
          "url": "https://www.mainz.de/angebote-entdecken/freizeit/feste-und-veranstaltungen/weihnachtsmarkt"}


def scrape(ctx):
    return seasonal(ctx, SOURCE, "Mainzer Weihnachtsmarkt", "Domplatz", "Mainz", "Domplatz, 55116 Mainz",
                    near=r"Weihnachtsmarkt findet")
