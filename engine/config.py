import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path=None):
    with open(path or os.path.join(HERE, "requirements.json"), encoding="utf-8") as f:
        return json.load(f)


def term_window(cfg, name, year):
    """Dates for a term. 'Spring 2027' runs 12/2/2026 - 5/1/2027 (year = the year it ends)."""
    t = cfg["terms"][name]
    sm, sd = (int(x) for x in t["start"].split("-"))
    em, ed = (int(x) for x in t["end"].split("-"))
    if name == "Spring":
        return date(year - 1, sm, sd), date(year, em, ed)
    return date(year, sm, sd), date(year, em, ed)


def term_for_date(cfg, d):
    """Return (term name, term year) that contains date d."""
    for year in (d.year, d.year + 1):
        for name in cfg["terms"]:
            s, e = term_window(cfg, name, year)
            if s <= d <= e:
                return name, year
    raise ValueError(f"No term found for {d}")
