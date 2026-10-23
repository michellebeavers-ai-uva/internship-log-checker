"""Entry points used by both the command line and the browser page."""
import hashlib
import json
import os
from datetime import date, datetime

from .config import load_config, term_for_date, term_window
from .parse import read_workbook
from .reports import end_html, feedback_html, start_html
from .rules import analyze, infer_statuses


def _today(iso):
    return datetime.strptime(iso, "%Y-%m-%d").date() if iso else date.today()


def _term(cfg, term, year, today):
    if term and year:
        return term, int(year)
    return term_for_date(cfg, today)


def inspect_workbook(source, term=None, year=None, today=None):
    """Step 1: read the file and guess each course's status for the chosen term."""
    cfg = load_config()
    today = _today(today)
    term, year = _term(cfg, term, year, today)
    start, end = term_window(cfg, term, year)
    model = read_workbook(source, cfg)
    statuses = infer_statuses(model, start, end)
    courses = []
    for code, tab in model.tabs.items():
        acts = tab.activities
        courses.append({"code": code, "name": cfg["courses"][code]["name"], "status": statuses[code],
                        "hours": sum(a.hours for a in acts), "entries": len(acts),
                        "dated": sum(1 for a in acts if a.date)})
    pathways = {k: {"label": v["label"], "experience_only": v["experience_only"]}
                for k, v in cfg["pathways"].items() if not k.startswith("_")}
    return {"term": term, "year": year, "detected_pathway": model.pathway_hint or "standard", "pathways": pathways,
            "course_names": {c: v["name"] for c, v in cfg["courses"].items()}, "start": start.isoformat(), "end": end.isoformat(),
            "courses": courses, "missing_tabs": model.missing_tabs,
            "library_entries": len(model.library), "has_completed_column": model.has_completed_column}


def _fingerprint(source):
    """First 12 characters of the file's SHA-256: names the exact file version without revealing anything about it."""
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    elif isinstance(source, str) and os.path.isfile(source):
        with open(source, "rb") as f:
            data = f.read()
    else:
        return ""
    return hashlib.sha256(data).hexdigest()[:12]


def run(source, term=None, year=None, statuses=None, pathway="auto", student_id="", today=None, file_name=None):
    """Step 2: run every check and build the three documents."""
    cfg = load_config()
    today = _today(today)
    term, year = _term(cfg, term, year, today)
    start, end = term_window(cfg, term, year)
    model = read_workbook(source, cfg)
    if pathway in (None, "", "auto"):
        pathway = model.pathway_hint or "standard"
    st = infer_statuses(model, start, end)
    st.update({k: v for k, v in (statuses or {}).items() if k in st})
    result = analyze(model, cfg, term, year, st, today=today, pathway=pathway)
    choice = [a for t in model.tabs.values() for a in t.activities if a.kind == "CHOICE"]
    result["run_info"] = {
        "student_id": student_id,
        "file_name": file_name or (os.path.basename(source) if isinstance(source, str) else ""),
        "fingerprint": _fingerprint(source),
        "program": result["pathway_label"] or "Standard (5 semesters)",
        "current": [c for c, v in st.items() if v == "current"],
        "completed": [c for c, v in st.items() if v == "completed"],
        "not_selected": [c for c, v in st.items() if v == "future"],
        "rule": result["done"]["mode"],
        "choice_read": len(choice),
        "not_counted": len(result["excluded"]),
        "sample_copies": sum(1 for f in result["lib_flags"].values() if f["kind"] == "exact"),
        "version": cfg.get("version", ""),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    docs = {"feedback": feedback_html(result, student_id),
            "start": start_html(result, student_id),
            "end": end_html(result, student_id)}
    return result, docs


# ---- JSON wrappers for the browser (arguments and results are plain strings)
def inspect_json(path, term="", year="", today=""):
    try:
        return json.dumps(inspect_workbook(path, term or None, year or None, today or None))
    except Exception as e:  # noqa: BLE001 - show a friendly message in the page
        return json.dumps({"error": f"Could not read this file as the A&S Planning Log: {e}"})


def run_json(path, options_json):
    try:
        o = json.loads(options_json)
        result, docs = run(path, o.get("term") or None, o.get("year") or None, o.get("statuses"),
                           o.get("pathway", "auto"), o.get("student_id", ""), o.get("today") or None,
                           o.get("file_name") or None)
        counts = {s: sum(1 for f in result["findings"] if f["severity"] == s)
                  for s in ("action", "check", "tip", "info", "ok")}
        return json.dumps({"counts": counts, "reports": docs})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": f"Something went wrong while checking the file: {e}"})
