"""Scraper registry. Each module exposes SOURCE = {id, name, url} and scrape(ctx) -> list[event]."""
import importlib

MODULES = [
    "staatstheater_wiesbaden", "kurhaus_wiesbaden", "termine_kurhaus", "schlachthof_wiesbaden",
    "staatstheater_mainz", "frankfurter_hof_mainz", "kuz_mainz", "mainz_klassik",
    "alte_oper", "oper_frankfurt", "hr_sinfonieorchester", "batschkapp", "jahrhunderthalle", "festhalle",
    "staatstheater_darmstadt", "centralstation_darmstadt",
    "english_theatre", "staedel", "schirn", "museum_wiesbaden", "kunsthalle_mainz",
    "eventbrite", "luma", "ihk_frankfurt", "datamonster",
    "buchmesse", "xmas_frankfurt", "xmas_wiesbaden", "xmas_mainz",
]


def load(name):
    return importlib.import_module(f"{__name__}.{name}")
