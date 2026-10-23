"""Build the three student-facing documents as self-contained, printable HTML strings."""
from datetime import date
from html import escape as esc

from .textcheck import is_placeholder

CSS = """
:root{--blue:#232D4B;--orange:#E57200;--gray:#F1F1EF;--gray2:#DADADA;--ink:#111111;--muted:#666666;
--blue25:#C8CBD2;--orange25:#F9DCBF;--cyan:#009FDF;--green:#62BB46;--yellow:#FDDA24}
*{box-sizing:border-box}
body{font-family:"Franklin Gothic Book","Libre Franklin","Franklin Gothic Medium",Arial,Helvetica,sans-serif;color:var(--ink);
background:#fff;margin:0;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.band{background:var(--blue);color:#fff;padding:1.15rem 2rem 1rem;border-bottom:6px solid var(--orange)}
.band .l1{font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;color:#fff;opacity:.92}
.band .l2{font-family:"Adobe Caslon Pro","Libre Caslon Text",Georgia,"Times New Roman",serif;font-size:1.65rem;line-height:1.2;margin:.15rem 0 .1rem}
.band .l3{font-size:.85rem;color:var(--blue25)}
main{max-width:900px;margin:0 auto;padding:1.4rem 2rem 2.2rem}
h1,h2,h3{font-family:"Adobe Caslon Pro","Libre Caslon Text",Georgia,"Times New Roman",serif;color:var(--blue);font-weight:700}
h1{font-size:1.75rem;margin:.2rem 0 .15rem;line-height:1.2}
h2{font-size:1.28rem;margin:2rem 0 .55rem;padding-bottom:.2rem;border-bottom:3px solid var(--orange)}
h3{font-size:1.02rem;margin:1.2rem 0 .3rem}
p{margin:.4rem 0}.sub{color:var(--muted);margin:0 0 1rem;font-size:.95rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1rem;font-size:.9rem}
th,td{text-align:left;padding:.42rem .55rem;border-bottom:1px solid var(--gray2);vertical-align:top}
th{background:var(--blue);color:#fff;font-weight:700;border-bottom:0}
tbody tr:nth-child(even) td{background:var(--gray)}
td.n,th.n{text-align:right;white-space:nowrap}
.chip{display:inline-block;padding:.05rem .5rem;border-radius:3px;font-size:.8rem;font-weight:700;white-space:nowrap;color:var(--ink)}
.chip.long{white-space:normal;max-width:12rem;margin-top:.15rem}td.w,th.w{width:42%}
table.compact{table-layout:fixed;font-size:.76rem;line-height:1.28}table.compact th,table.compact td{padding:.26rem .38rem;word-wrap:break-word;overflow-wrap:break-word}
table.compact th{font-size:.7rem}
table.compact .chip{font-size:.7rem;white-space:normal;max-width:none}
.legend{font-size:.76rem;color:var(--muted);margin:.2rem 0 .1rem}
.met{background:var(--green)}.need{background:var(--orange)}.check{background:var(--yellow)}.tip{background:var(--cyan)}
.note{background:var(--gray);color:var(--blue);border:1px solid var(--gray2)}.gone{background:var(--blue25);color:var(--blue)}
.finding{border-left:6px solid var(--gray2);padding:.4rem .9rem;margin:.65rem 0;background:#fff;box-shadow:0 0 0 1px var(--gray2) inset}
.finding.action{border-left-color:var(--orange)}.finding.check{border-left-color:var(--yellow)}
.finding.tip{border-left-color:var(--cyan)}.finding.ok{border-left-color:var(--green)}.finding.info{border-left-color:var(--blue25)}
.finding h4{margin:.1rem 0;font-size:1rem;color:var(--blue)}.finding ul{margin:.3rem 0 .2rem 1.1rem;padding:0}
.box{background:var(--gray);padding:.75rem 1rem;border-left:6px solid var(--orange);margin:.9rem 0}
.tiles{margin:.9rem 0 .4rem;font-size:0}
.tile{display:inline-block;vertical-align:top;width:32%;margin:0 1.3% .5rem 0;background:var(--gray);border-top:5px solid var(--orange);padding:.6rem .9rem}
.tile:last-child{margin-right:0}.tile{min-height:5.4rem}
.tile b{display:block;font-family:"Adobe Caslon Pro","Libre Caslon Text",Georgia,serif;font-size:2rem;line-height:1.1;color:var(--blue)}
.tile span{display:block;font-size:.85rem;color:var(--ink);font-weight:700;margin-top:.1rem}
.bar{background:var(--gray2);height:16px;margin:.3rem 0 .15rem}.bar i{display:block;background:var(--orange);height:16px}
.barlabel{font-size:.85rem;color:var(--muted)}
.foot{margin-top:2.4rem;color:var(--muted);font-size:.8rem;border-top:3px solid var(--blue);padding-top:.6rem}
.foot b{color:var(--blue)}
.run{font-size:.82rem;margin:.4rem 0 0}.run td{padding:.25rem .55rem}.run td:first-child{width:30%;font-weight:700;color:var(--blue)}
.runnote{font-size:.85rem;color:var(--muted);margin:.2rem 0}
@page{margin:.5in}
@media print{.band{padding:.9rem 1.2rem .8rem}main{padding:1rem 1.2rem}h2{break-after:avoid}table,.finding,.tile{break-inside:avoid}}
"""

SEV_LABEL = {"action": ("Fix now", "need"), "check": ("Check", "check"), "tip": ("Tip", "tip"),
             "info": ("Note", "note"), "ok": ("Met", "met")}


def _h(x):
    return f"{x:g}"


def _fmt(d):
    return f"{d.month}/{d.day}/{d.year}"


def _brand(result):
    b = {"line1": "UVA School of Education", "line2": "Administration & Supervision", "line3": "Internship Program"}
    b.update({k: v for k, v in (result.get("cfg", {}).get("branding", {}) or {}).items() if not k.startswith("_")})
    return b


def _page(title, body, result):
    b = _brand(result)
    band = (f"<div class='band'><div class='l1'>{esc(b['line1'])}</div><div class='l2'>{esc(b['line2'])}</div>"
            f"<div class='l3'>{esc(b['line3'])}</div></div>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)}</title><style>{CSS}</style></head><body>{band}<main>{body}</main></body></html>")


def _head(result, title, student_id):
    t = result["term"]
    who = f"Student ID: {esc(student_id)} · " if student_id else ""
    if result.get("pathway") not in (None, "standard") and result.get("pathway_label"):
        who += f"{esc(result['pathway_label'])} · "
    return (f"<h1>{esc(title)}</h1><p class='sub'>{who}{t['name']} {t['year']} "
            f"({_fmt(t['start'])} – {_fmt(t['end'])}) · prepared {_fmt(result['today'])}</p>")


def _foot(result=None, mentor=False):
    b = _brand(result or {})
    if mentor:
        return (f"<p class='foot'><b>{esc(b['line1'])}: {esc(b['line2'])}</b> · {esc(b['line3'])}<br>"
                "This summary was generated from the student's planning log by rule-based checks (no AI). It lists only experiences "
                "the student marked Completed, and it leaves out entries that repeat an earlier entry. The Canvas tracking form is "
                "the official record.</p>")
    return (f"<p class='foot'><b>{esc(b['line1'])}: {esc(b['line2'])}</b> · {esc(b['line3'])}<br>"
            "This report was generated from your planning log by rule-based checks. It does not use AI, and your file was "
            "not uploaded anywhere. Hours count only for complete, original entries: a later entry that repeats an earlier "
            "one is not counted. The planning log is your plan; the Canvas tracking form is the official record.</p>")


def _run_details(result):
    """What the student entered and what was read, so a question like "this report isn't right" can be answered quickly."""
    ri = result.get("run_info")
    if not ri:
        return ""
    show_name = (result.get("cfg", {}).get("report", {}) or {}).get("show_file_name", True)
    names = lambda codes: "; ".join(f"{c} – {esc(result['courses'][c]['name'])}" for c in codes) or "none selected"
    t = result["term"]
    rule = ("the Completed column" if ri["rule"] == "column"
            else "the entry's date (on or before today); this log has no Completed column")
    rows = [("Student ID", esc(ri["student_id"] or "(not entered)"))]
    if show_name:
        rows.append(("Planning log file", esc(ri["file_name"] or "(unknown)")))
    rows += [
        ("File fingerprint", f"{esc(ri['fingerprint'] or '—')} (identifies this exact version of the file)"),
        ("Semester", f"{t['name']} {t['year']} ({_fmt(t['start'])} – {_fmt(t['end'])})"),
        ("Program", esc(ri["program"])),
        ("Currently enrolled", names(ri["current"])),
        ("Already completed", names(ri["completed"])),
        ("Not selected (later courses)", esc(", ".join(ri["not_selected"]) or "none")),
        ("\"Completed\" decided by", rule),
        ("CHOICE entries read", f"{ri['choice_read']} ({ri['not_counted']} not counted, {ri['sample_copies']} copied from a sample)"),
        ("Checker version / run", f"{esc(ri['version'])} · {esc(ri['generated'])}"),
    ]
    body = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    return ("<h2>Run details (for troubleshooting)</h2>"
            "<p class='runnote'>If something in this report looks wrong, send this box (and your log file) to your supervisor.</p>"
            f"<table class='run'><tbody>{body}</tbody></table>")


def _tiles(items):
    """items: [(big text, label), ...]"""
    return "<div class='tiles'>" + "".join(f"<div class='tile'><b>{esc(str(n))}</b><span>{esc(lbl)}</span></div>"
                                           for n, lbl in items) + "</div>"


def _bar(value, total, label):
    pct = 0 if total <= 0 else max(0, min(100, round(100 * value / total)))
    return f"<div class='bar'><i style='width:{pct}%'></i></div><div class='barlabel'>{esc(label)} ({pct}%)</div>"


def _chip(kind, text, long=False):
    return f"<span class='chip {kind}{' long' if long else ''}'>{esc(text)}</span>"


def _table(headers, rows, num_cols=(), wide_cols=(), widths=None):
    """widths: column widths in percent. Giving widths makes a compact, fixed-layout table (long text wraps inside its column)."""
    cls = lambda i: ("n" if i in num_cols else "") + (" w" if i in wide_cols and not widths else "")
    th = "".join(f"<th class='{cls(i)}'>{esc(h)}</th>" for i, h in enumerate(headers))
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td class='{cls(i)}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    group = "<colgroup>" + "".join(f"<col style='width:{w}%'>" for w in widths) + "</colgroup>" if widths else ""
    return f"<table{' class=\"compact\"' if widths else ''}>{group}<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def _finding_html(f):
    label, cls = SEV_LABEL[f["severity"]]
    items = "".join(f"<li>{esc(i)}</li>" for i in f["items"])
    detail = f"<p>{esc(f['detail'])}</p>" if f["detail"] else ""
    return (f"<div class='finding {f['severity']}'><h4>{_chip(cls, label)} {esc(f['title'])}</h4>"
            f"{detail}{'<ul>' + items + '</ul>' if items else ''}</div>")


def _course_status(c):
    if c["logged"] >= c["target"]:
        return _chip("met", "Met")
    return _chip("need", f"{_h(c['hours_remaining'])} to go")


def _courses_table(result, codes):
    rows = []
    for code in codes:
        c = result["courses"][code]
        rows.append([f"{code} – {esc(c['name'])}", _h(c["fixed"]),
                     f"{_h(c['choice_logged'])} / {_h(c['choice_needed'])}",
                     f"{_h(c['logged'])} / {_h(c['target'])}", _course_status(c)])
    if not rows:
        return "<p>None recorded.</p>"
    return _table(["Course", "Embedded + aligned", "Choice (planned / needed)", "Total / target", "Status"],
                  rows, num_cols=(1, 2, 3))


def _codes(result, status):
    return [c for c, v in result["courses"].items() if v["status"] == status]


def _competency_table(result):
    rows = []
    for c in result["competencies"]:
        if c["min"] == 0 and c["total"] == 0:
            status = _chip("note", "No minimum")
        elif c["remaining"] <= 0:
            status = _chip("met", "Met")
        else:
            status = _chip("need", f"{_h(c['remaining'])} to go")
        rows.append([f"{c['n']}. {esc(c['name'])}", _h(c["min"]), _h(c["completed"]), _h(c["current"]),
                     _h(c["future"]), _h(c["total"]), status])
    return _table(["Competency (CHOICE hours)", "Minimum", "Earlier courses", "This semester", "Later plans",
                   "Total", "Status"], rows, num_cols=(1, 2, 3, 4, 5))


def _external_table(result):
    ext = result["external"]
    rows = []
    for e in ext["rows"]:
        if e["min"] is None:
            status = _chip("note", "Counts toward total")
            mn = "—"
        else:
            mn = _h(e["min"])
            status = _chip("met", "Met") if e["remaining"] <= 0 else _chip("need", f"{_h(e['remaining'])} to go")
        rows.append([esc(e["type"]), mn, _h(e["completed"]), _h(e["current"]), _h(e["future"]), _h(e["total"]), status])
    if ext["total_remaining"] > 0:
        tot_status = _chip("need", f"{_h(ext['total_remaining'])} to go")
    elif ext["types_met"] < ext["types_needed"]:
        tot_status = _chip("need", "Spread across more site types")
    else:
        tot_status = _chip("met", "Met")
    rows.append(["<b>Total outside your building</b>", _h(ext["total_min"]), "", "", "", f"<b>{_h(ext['total'])}</b>", tot_status])
    return _table(["Site type", "Minimum", "Earlier courses", "This semester", "Later plans", "Total", "Status"],
                  rows, num_cols=(1, 2, 3, 4, 5))


def _suggestions(result, k=3):
    """Choice Library ideas for current courses that still need CHOICE hours."""
    comps = sorted((c for c in result["competencies"] if c["remaining"] > 0),
                   key=lambda c: -c["remaining"])[:2]
    wanted = {c["n"] for c in comps}
    if not wanted:
        return ""
    out = ""
    for code in _codes(result, "current"):
        c = result["courses"][code]
        if c["choice_remaining"] <= 0:
            continue
        picks = [e for e in result["model"].library if e.course == code and e.comp in wanted][:k]
        if picks:
            lis = "".join(f"<li>{esc(e.text)} <i>(competency {e.comp})</i></li>" for e in picks)
            out += f"<h3>{code} – {esc(c['name'])}: {_h(c['choice_remaining'])} CHOICE hours to plan</h3><ul>{lis}</ul>"
    if not out:
        return ""
    names = " and ".join(f"{c['n']} ({esc(c['name'])})" for c in comps)
    return (f"<h2>Ideas for your remaining CHOICE hours</h2>"
            f"<p>You are furthest from the minimum in competency {names}. These Choice Library ideas fit your courses. "
            "Rewrite any you use in your own words.</p>" + out)


def _group_findings(result, severities):
    fs = [f for f in result["findings"] if f["severity"] in severities]
    return "".join(_finding_html(f) for f in fs) or "<p>Nothing to fix here.</p>"


# ------------------------------------------------------------------ documents
def _flag_chips(result, a):
    """Chips for an entry that does not count, or that copies a Choice Library sample."""
    key = (a.course, a.row)
    ex = result["excluded"].get(key)
    if ex:
        if ex["reason"] == "duplicate":
            oc, orow = ex["of"]
            return _chip("gone", f"Not counted: repeats {oc} row {orow}", long=True)
        return _chip("gone", "Not counted: copied from a sample", long=True)
    f = result["lib_flags"].get(key)
    if f:
        kind = f["kind"]
        return _chip("need" if kind == "exact" else "check",
                     {"exact": "Copied from a sample", "contains": "Contains sample wording", "near": "Very close to a sample"}[kind],
                     long=True)
    return ""


def _activity_table(result, code, with_status):
    model, today = result["model"], result["today"]
    use_column = result["done"]["mode"] == "column"
    rows = []
    for a in model.tabs[code].activities:
        if a.hours == 0 and is_placeholder(a.description):
            continue                      # untouched placeholder row: not an experience yet
        desc = a.description or "(no description)"
        desc = desc if len(desc) <= 140 else desc[:137] + "..."
        counted = (a.course, a.row) not in result["excluded"]
        row = [a.kind.title(), _fmt(a.date) if a.date else "—", esc(a.location or "—"),
               esc(a.role or "—"), _h(a.hours) if counted else f"<s>{_h(a.hours)}</s>", esc(desc)]
        flag = _flag_chips(result, a)
        if with_status:
            done = a.completed if use_column else bool(a.date and a.date <= today)
            row.append(" ".join(x for x in (_chip("met", "Completed") if done else _chip("check", "Not completed"), flag) if x))
        else:
            row.append(flag or "—")
        rows.append(row)
    heads = ["Type", "Date", "Location", "Role", "Hrs", "Description", "Status" if with_status else "Flag"]
    return _table(heads, rows, num_cols=(4,), widths=[10, 10, 12, 12, 5, 35, 16])


def feedback_html(result, student_id=""):
    f = result["findings"]
    n = {s: sum(1 for x in f if x["severity"] == s) for s in ("action", "check", "tip")}
    summary = _tiles([(n["action"], "to fix now"), (n["check"], "to check"), (n["tip"], "tips for stronger entries")])
    body = _head(result, "Planning log feedback", student_id) + summary
    body += "<h2>What to work on</h2>" + _group_findings(result, ("action", "check", "tip", "info"))
    body += "<h2>What is already in good shape</h2>" + _group_findings(result, ("ok",))
    body += "<h2>Hours by course</h2><h3>This semester</h3>" + _courses_table(result, _codes(result, "current"))
    body += "<h3>Earlier courses</h3>" + _courses_table(result, _codes(result, "completed"))
    body += "<h2>Competency hours (CHOICE only, whole program)</h2>" + _competency_table(result)
    body += "<h2>Hours outside your own building</h2>" + _external_table(result)
    return _page("Planning log feedback", body + _run_details(result) + _foot(result), result)


def start_html(result, student_id=""):
    """Start of semester: the courses the student is enrolled in now, and their plan."""
    cur = _codes(result, "current")
    body = _head(result, "Start-of-semester plan", student_id)
    open_items = sum(1 for f in result["findings"] if f["course"] in cur and f["severity"] in ("action", "check"))
    body += _tiles([(len(cur), "courses this semester"),
                    (_h(sum(result["courses"][c]["logged"] for c in cur)), "hours planned (counted)"),
                    (open_items, "open items")])
    body += ("<div class='box'>Courses and experience blocks this semester: <b>"
             + (", ".join(f"{c} – {esc(result['courses'][c]['name'])}" for c in cur) or "none selected")
             + "</b></div>")
    body += "<h2>Planned hours</h2>" + _courses_table(result, cur)
    for code in cur:
        body += f"<h3>{code} – {esc(result['courses'][code]['name'])}: planned experiences</h3>"
        body += _activity_table(result, code, with_status=False)
    fs = [f for f in result["findings"] if f["course"] in cur and f["severity"] in ("action", "check")]
    body += "<h2>To finish before the semester gets going</h2>"
    body += "".join(_finding_html(f) for f in fs) or "<p>Your plan for this semester has no open items.</p>"
    body += _suggestions(result)
    return _page("Start-of-semester plan", body + _run_details(result) + _foot(result), result)


def _status_to_go(left):
    return _chip("met", "Met") if left <= 0 else _chip("need", f"{_h(left)} to go")


def end_html(result, student_id=""):
    """End of semester: this semester, previous courses, and the final cumulative totals."""
    cfg, d, tot = result["cfg"], result["done"], result["totals"]
    prog = cfg["program"]
    cur = _codes(result, "current")
    body = _head(result, "End-of-semester summary", student_id)
    rule = ("an activity counts as completed when its <b>Completed</b> column is marked"
            if d["mode"] == "column" else
            "an activity counts as completed when it has a date on or before "
            f"{_fmt(result['today'])} (your log has no Completed column)")
    body += (f"<div class='box'>In this report, {rule}. Courses you listed as completed earlier count every hour "
             "entered. Enter completed hours in the Canvas tracking form.</div>")

    h = d["hours"]
    body += _tiles([(_h(h["current"]), "hours this semester (completed)"), (_h(h["previous"]), "hours in previous courses"),
                    (f"{_h(h['cumulative'])} / {_h(tot['target'])}", "cumulative toward the minimum")])
    body += _bar(h["cumulative"], tot["target"], f"{_h(h['cumulative'])} of {_h(tot['target'])} hours completed")
    body += "<h2>Hours summary</h2>" + _table(
        ["", "Hours", "Status"],
        [["This semester (completed)", _h(h["current"]), ""],
         ["Previous courses", _h(h["previous"]), ""],
         ["<b>Cumulative</b>", f"<b>{_h(h['cumulative'])}</b>",
          _status_to_go(tot["target"] - h["cumulative"]) + f" of {_h(tot['target'])} minimum"]],
        num_cols=(1,))

    body += "<h2>This semester</h2>"
    rows = []
    for code in cur:
        c = result["courses"][code]
        left = max(0.0, c["target"] - c["done_hours"])
        rows.append([f"{code} – {esc(c['name'])}", _h(c["logged"]), _h(c["done_hours"]),
                     _h(c["not_done_hours"]), _h(c["target"]),
                     _chip("met", "Complete") if left <= 0 else _chip("need", f"{_h(left)} to go")])
    body += (_table(["Course", "Planned", "Completed", "Not yet completed", "Target", "Status"], rows,
                    num_cols=(1, 2, 3, 4)) if rows else "<p>No current courses selected.</p>")
    for code in cur:
        body += f"<h3>{code} – {esc(result['courses'][code]['name'])}</h3>" + _activity_table(result, code, True)

    crow, short_comp = [], []
    for c in result["competencies"]:
        x = d["competency"][c["n"]]
        cum = x["current"] + x["previous"]
        left = max(0.0, c["min"] - cum)
        if left > 0:
            short_comp.append((c, cum, left))
        st = _chip("note", "No minimum") if c["min"] == 0 and cum == 0 else _status_to_go(left)
        crow.append([f"{c['n']}. {esc(c['name'])}", _h(c["min"]), _h(x["current"]), _h(x["previous"]), _h(cum), st])
    body += "<h2>Competency hours (completed CHOICE hours)</h2>" + _table(
        ["Competency", "Minimum", "This semester", "Previous", "Cumulative", "Status"], crow, num_cols=(1, 2, 3, 4))

    erow, ext_cum, types_met, short_ext = [], 0.0, 0, []
    cur_tot = prev_tot = 0.0
    for t in prog["external_types"] + ["Other"]:
        x = d["external"][t]
        cum = x["current"] + x["previous"]
        ext_cum += cum
        cur_tot += x["current"]
        prev_tot += x["previous"]
        if t == "Other":
            erow.append([t, "—", _h(x["current"]), _h(x["previous"]), _h(cum), _chip("note", "Counts toward total")])
        else:
            left = max(0.0, prog["external_min_per_type"] - cum)
            types_met += left <= 0
            if left > 0:
                short_ext.append(t)
            erow.append([t, _h(prog["external_min_per_type"]), _h(x["current"]), _h(x["previous"]), _h(cum),
                         _status_to_go(left)])
    if ext_cum < prog["external_total_min"]:
        tchip = _status_to_go(prog["external_total_min"] - ext_cum)
    elif types_met < prog["external_types_needed"]:
        tchip = _chip("need", "Spread across more site types")
    else:
        tchip = _chip("met", "Met")
    erow.append(["<b>Total outside your building</b>", _h(prog["external_total_min"]), _h(cur_tot),
                 _h(prev_tot), f"<b>{_h(ext_cum)}</b>", tchip])
    body += "<h2>Hours outside your own building (completed)</h2>" + _table(
        ["Site type", "Minimum", "This semester", "Previous", "Cumulative", "Status"], erow, num_cols=(1, 2, 3, 4))

    body += "<h2>Previous courses</h2>" + _courses_table(result, _codes(result, "completed"))

    carry = []
    for code in cur:
        c = result["courses"][code]
        if c["target"] - c["done_hours"] > 0:
            carry.append(f"{code}: {_h(c['target'] - c['done_hours'])} hours not yet completed")
    for c, cum, left in short_comp:
        carry.append(f"Competency {c['n']} ({c['name']}): {_h(left)} more CHOICE hours needed "
                     f"({_h(cum)} of {_h(c['min'])} completed)")
    if ext_cum < prog["external_total_min"] or short_ext:
        carry.append("External hours: " + (f"{_h(prog['external_total_min'] - ext_cum)} more needed; "
                                           if ext_cum < prog["external_total_min"] else "")
                     + ("site types under " + _h(prog["external_min_per_type"]) + " hours: " + ", ".join(short_ext)
                        if short_ext else ""))
    body += "<h2>Still needed to meet program requirements</h2>"
    body += ("<ul>" + "".join(f"<li>{esc(i)}</li>" for i in carry) + "</ul>") if carry else "<p>All requirements are met.</p>"
    return _page("End-of-semester summary", body + _run_details(result) + _foot(result), result)


# ------------------------------------------------------------------ Mentor report
def _is_done(result, a):
    """Same rule the end-of-semester report uses: the Completed column, or (older logs) a date on or before today."""
    if result["done"]["mode"] == "column":
        return a.completed
    return bool(a.date and a.date <= result["today"])


GLYPHS = "①②③④⑤⑥"


def _comp_glyph(a):
    """The circled competency number(s), like the log's All CHOICE tab."""
    return "".join(GLYPHS[n - 1] for n in a.comps) if a.comps else "—"


def _short(text, n):
    text = text or "(no description)"
    return text if len(text) <= n else text[:n - 3] + "..."


def mentor_html(result, student_id=""):
    """For mentors: what was completed in earlier semesters, what was completed this semester (per course), and every
    CHOICE experience completed this semester. Only counted entries are listed; repeats of an earlier entry are left out."""
    cur, prev = _codes(result, "current"), _codes(result, "completed")
    model, excluded = result["model"], result["excluded"]
    done_rows, choice, omitted = {}, [], 0
    for code in cur:
        rows = []
        for a in model.tabs[code].activities:
            if not _is_done(result, a) or a.hours <= 0:
                continue
            if (a.course, a.row) in excluded:
                omitted += 1
                continue
            rows.append(a)
        done_rows[code] = rows
        choice += [a for a in rows if a.kind == "CHOICE"]
    d = result["done"]["hours"]
    choice_hours = sum(a.hours for a in choice)

    body = _head(result, "Mentor summary", student_id)
    body += _tiles([(_h(d["current"]), "hours completed this semester"), (_h(d["previous"]), "hours completed in earlier semesters"),
                    (_h(choice_hours), "CHOICE hours completed this semester")])

    # ---- earlier semesters
    body += "<h2>Completed in earlier semesters</h2>"
    if prev:
        rows = [[f"{c} – {esc(result['courses'][c]['name'])}", _h(result["courses"][c]["fixed"]),
                 _h(result["courses"][c]["choice_logged"]), _h(result["courses"][c]["logged"])] for c in prev]
        rows.append(["<b>Total</b>", "", "", f"<b>{_h(d['previous'])}</b>"])
        body += _table(["Course", "Embedded + aligned hours", "CHOICE hours", "Total hours"], rows, num_cols=(1, 2, 3))
    else:
        body += "<p>No earlier courses were selected as completed.</p>"

    # ---- this semester, per course
    body += "<h2>Completed this semester, by course</h2>"
    if not cur:
        body += "<p>No courses were selected for this semester.</p>"
    for code in cur:
        c = result["courses"][code]
        body += f"<h3>{code} – {esc(c['name'])}</h3>"
        rows = done_rows[code]
        if not rows:
            body += "<p>No experiences are marked Completed yet.</p>"
            continue
        trs = [[a.kind.title(), _fmt(a.date) if a.date else "—", esc(a.location or "—"), esc(a.role or "—"), _h(a.hours),
                esc(_short(a.description, 70 if a.kind != "CHOICE" else 10_000))] for a in rows]
        trs.append(["", "", "", "<b>Completed</b>", f"<b>{_h(sum(a.hours for a in rows))}</b>",
                    f"of {_h(c['logged'])} hours planned for this course"])
        body += _table(["Type", "Date", "Location", "Role", "Hrs", "Experience"], trs, num_cols=(4,), widths=[11, 10, 13, 12, 5, 49])

    # ---- every CHOICE experience completed this semester, laid out like the log's All CHOICE tab
    body += "<h2>All CHOICE experiences completed this semester</h2>"
    if choice:
        key = " &nbsp;·&nbsp; ".join(f"{GLYPHS[int(n) - 1]} {esc(v['name'])}" for n, v in result["cfg"]["competencies"].items())
        body += f"<p class='legend'>Competency: {key}</p>"
        ordered = sorted(choice, key=lambda a: (a.date is None, a.date or date.max, a.course, a.row))
        trs = [[_comp_glyph(a), _fmt(a.date) if a.date else "—", esc(a.site or "—"), esc(a.location or "—"),
                esc(a.description or "(no description)"), esc(a.role or "—"), _h(a.hours), a.course] for a in ordered]
        trs.append(["", "", "", "", "", "<b>Total</b>", f"<b>{_h(choice_hours)}</b>", ""])
        body += _table(["Competency", "Date", "Name the Location", "Type", "Experience", "Role", "Hours", "Course"], trs,
                       num_cols=(6,), widths=[11, 9, 13, 11, 31, 11, 6, 8])
    else:
        body += "<p>No CHOICE experiences are marked Completed this semester.</p>"
    if omitted:
        body += (f"<p class='runnote'>{omitted} completed entr{'y' if omitted == 1 else 'ies'} that repeat an earlier entry "
                 "are not counted and are not listed.</p>")
    return _page("Mentor summary", body + _foot(result, mentor=True), result)
