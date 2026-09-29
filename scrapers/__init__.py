"""Scraper registry. Each module exposes SOURCE = {id, name, url} and scrape(ctx) -> list[event]."""
import importlib

MODULES = [
    "staatstheater_wiesbaden", "kurhaus_wiesbaden", "termine_kurhaus", "schlachthof_wiesbaden",
    "staatstheater_mainz", "frankfurter_hof_mainz", "kuz_mainz", "mainz_klassik",
    "alte_oper", "oper_frankfurt", "hr_sinfonieorchester", "batschkapp", "jahrhunderthalle", "festhalle",
    "staatstheater_darmstadt", "centralstation_darmstadt",
    "english_theatre", "staedel", "schirn", "museum_wiesbaden", "kunsthalle_mainz",
    "eventbrite", "luma", "ihk_frankfurt", "datamonster",
    "studiobloc_wiesbaden", "nordwand_wiesbaden", "boulderwelt_frankfurt", "kletterkiste_mainz",
    "lc_olympia", "rheinrunners", "dav_waldlaeufer", "tuesday_night_run", "meenzrunners", "parkrun_maaraue",
    "buchmesse", "xmas_frankfurt", "xmas_wiesbaden", "xmas_mainz",
]


def load(name):
    return importlib.import_module(f"{__name__}.{name}")
