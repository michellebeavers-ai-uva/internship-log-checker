"""Rule checks. Every rule is deterministic and explained in plain language to the student."""
from collections import defaultdict
from datetime import date

from .config import term_window
from .textcheck import LibraryIndex, duplicate_score, is_placeholder, norm, quality_hints

SEV_ORDER = {"action": 0, "check": 1, "tip": 2, "info": 3, "ok": 4}


def finding(sev, cat, title, detail="", course=None, items=None):
    return {"severity": sev, "category": cat, "title": title, "detail": detail,
            "course": course, "items": items or []}


def _h(x):
    return f"{x:g}"


# ---------------------------------------------------------------- statuses
def infer_statuses(model, term_start, term_end):
    """Guess each course's status for the chosen term: completed / current / future."""
    out = {}
    for code, tab in model.tabs.items():
        dates = [a.date for a in tab.activities if a.date]
        if any(term_start <= d <= term_end for d in dates):
            out[code] = "current"
        elif dates and all(d < term_start for d in dates):
            out[code] = "completed"
        elif dates and all(d > term_end for d in dates):
            out[code] = "future"
        elif dates:
            out[code] = "current"
        else:
            has_choice = any(a.kind == "CHOICE" for a in tab.activities)
            out[code] = "current" if has_choice else "future"
    return out


# ---------------------------------------------------------------- analysis
def analyze(model, cfg, term_name, term_year, statuses, today=None, pathway="standard"):
    today = today or date.today()
    prog = cfg["program"]
    t_start, t_end = term_window(cfg, term_name, term_year)
    loc_types = prog["external_types"]
    own = prog["own_building_label"]
    findings = []

    use_column = model.has_completed_column
    path_cfg = cfg.get("pathways", {}).get(pathway, {})
    experience_only = set(path_cfg.get("experience_only", []))

    def is_done(a):
        """Completed column when the workbook has one; otherwise a date on or before today."""
        return a.completed if use_column else bool(a.date and a.date <= today)

    # ---- which CHOICE entries COUNT.  The first entry (earliest date) counts; a later entry that repeats it does not.
    th = cfg["text"]
    lib = LibraryIndex(model.library)
    seq = [c for n in sorted(path_cfg.get("semesters", {}), key=int) for c in path_cfg["semesters"][n]] + sorted(experience_only)
    rank = {c: i for i, c in enumerate(seq)}
    cands = [a for tab in model.tabs.values() for a in tab.activities
             if a.kind == "CHOICE" and a.description and not is_placeholder(a.description)]
    cands.sort(key=lambda a: (a.date or date.max, rank.get(a.course, 99), a.row))
    kept, excluded = [], {}                       # excluded: (course, row) -> why it does not count
    for a in cands:
        na, hit = norm(a.description), None
        for (k, nk) in kept:
            sc = duplicate_score(na, nk, th["duplicate_similarity"])
            if sc >= th["duplicate_similarity"]:
                hit = (k, sc)
                break
        if hit:
            excluded[(a.course, a.row)] = {"reason": "duplicate", "of": (hit[0].course, hit[0].row), "score": hit[1]}
        else:
            kept.append((a, na))
    lib_flags = {}                                # (course, row) -> how closely it matches a Choice Library sample
    for a, _ in kept:
        kind, score, entry = lib.best_match(a.description, th["library_similarity"], th["exact_similarity"])
        if kind:
            lib_flags[(a.course, a.row)] = {"kind": kind, "score": score, "entry": entry}
    if not th.get("count_library_copies", True):
        for key, f in lib_flags.items():
            if f["kind"] == "exact":
                excluded[key] = {"reason": "sample", "of": None, "score": f["score"]}

    def H(a):
        """Hours that count: zero for an entry that repeats another or (optionally) copies a sample."""
        return 0.0 if (a.course, a.row) in excluded else a.hours

    # ---- per-course numbers
    courses = {}
    for code, tab in model.tabs.items():
        meta = cfg["courses"][code]
        target = meta.get("target", prog["course_target"])
        acts = tab.activities
        fixed = sum(H(a) for a in acts if a.kind != "CHOICE")
        choice = sum(H(a) for a in acts if a.kind == "CHOICE")
        logged = fixed + choice
        need = max(0.0, target - fixed)
        status = statuses.get(code, "future")
        if status == "completed":
            done = logged                     # a finished course counts every hour entered
        elif status == "current":
            done = sum(H(a) for a in acts if is_done(a))
        else:
            done = 0.0
        courses[code] = {
            "code": code, "name": meta["name"] + (" (experiences only)" if code in experience_only else ""),
            "experience_only": code in experience_only, "status": statuses.get(code, "future"),
            "target": target, "fixed": fixed, "choice_logged": choice, "logged": logged,
            "choice_needed": need, "choice_remaining": max(0.0, need - choice),
            "hours_remaining": max(0.0, target - logged),
            "done_hours": done, "not_done_hours": max(0.0, logged - done) if status == "current" else 0.0,
            "sheet_choice_needed": tab.sheet_choice_needed,
        }

    def status_of(code):
        return courses[code]["status"]

    active = [c for c in courses if status_of(c) in ("current", "completed")]
    current = [c for c in courses if status_of(c) == "current"]

    # ---- competency totals (choice hours, exactly one X)
    comp = {}
    for n, meta in cfg["competencies"].items():
        comp[n] = {"n": int(n), "name": meta["name"], "min": meta["choice_min"],
                   "completed": 0.0, "current": 0.0, "future": 0.0}
    for code, tab in model.tabs.items():
        for a in tab.activities:
            if a.kind == "CHOICE" and len(a.comps) == 1 and H(a) > 0:
                comp[str(a.comps[0])][status_of(code)] += H(a)
    leeway = prog["competency_leeway_hours"]
    for c in comp.values():
        c["total"] = c["completed"] + c["current"] + c["future"]
        c["remaining"] = max(0.0, c["min"] - c["total"])
        c["excess"] = max(0.0, c["total"] - c["min"])

    # ---- external hours
    ext = {t: {"type": t, "completed": 0.0, "current": 0.0, "future": 0.0} for t in loc_types + ["Other"]}
    no_location = 0.0
    for code, tab in model.tabs.items():
        for a in tab.activities:
            if H(a) <= 0:
                continue
            loc = a.location
            if loc == own:
                continue
            if loc in ext:
                ext[loc][status_of(code)] += H(a)
            elif status_of(code) in ("current", "completed"):
                no_location += H(a)
    minpt = prog["external_min_per_type"]
    for t, e in ext.items():
        e["total"] = e["completed"] + e["current"] + e["future"]
        if t == "Other":
            e["min"], e["remaining"] = None, None
        else:
            e["min"], e["remaining"] = minpt, max(0.0, minpt - e["total"])
    ext_total = sum(e["total"] for e in ext.values())
    types_met = sum(1 for t in loc_types if ext[t]["total"] >= minpt)
    external = {"rows": list(ext.values()), "total": ext_total, "total_min": prog["external_total_min"],
                "total_remaining": max(0.0, prog["external_total_min"] - ext_total),
                "types_met": types_met, "types_needed": prog["external_types_needed"],
                "no_location_hours": no_location}

    # ---- program totals
    totals = {
        "target": prog["total_hours"],
        "completed_courses_hours": sum(courses[c]["logged"] for c in courses if status_of(c) == "completed"),
        "current_courses_hours": sum(courses[c]["logged"] for c in current),
        "future_courses_hours": sum(courses[c]["logged"] for c in courses if status_of(c) == "future"),
    }
    totals["all"] = totals["completed_courses_hours"] + totals["current_courses_hours"] + totals["future_courses_hours"]

    # ---- completed hours: this semester vs previous courses
    done = {"mode": "column" if use_column else "date",
            "hours": {"current": 0.0, "previous": 0.0},
            "competency": {c["n"]: {"current": 0.0, "previous": 0.0} for c in comp.values()},
            "external": {t: {"current": 0.0, "previous": 0.0} for t in loc_types + ["Other"]}}
    for code, tab in model.tabs.items():
        st = status_of(code)
        if st == "future":
            continue
        bucket = "previous" if st == "completed" else "current"
        for a in tab.activities:
            if H(a) <= 0 or (st == "current" and not is_done(a)):
                continue
            done["hours"][bucket] += H(a)
            if a.kind == "CHOICE" and len(a.comps) == 1:
                done["competency"][a.comps[0]][bucket] += H(a)
            if a.location in done["external"]:
                done["external"][a.location][bucket] += H(a)
    done["hours"]["cumulative"] = done["hours"]["current"] + done["hours"]["previous"]

    # ================================================================ findings
    if totals["all"] >= totals["target"]:
        findings.append(finding("ok", "Hours", "Program total meets the minimum",
                                f"{_h(totals['all'])} hours planned; the program minimum is {_h(totals['target'])}."))
    else:
        findings.append(finding("info", "Hours", f"Program total: {_h(totals['all'])} of {_h(totals['target'])} minimum hours planned",
                                f"{_h(totals['target'] - totals['all'])} more hours to plan across your remaining courses."))
    if experience_only and any(c in current for c in experience_only):
        names = " and ".join(f"{c} – {cfg['courses'][c]['name']}" for c in sorted(experience_only))
        findings.append(finding("info", "Program", "Reminder for 2nd-MEd students",
                                cfg["second_med_reminder"].format(courses=names, total=_h(prog["total_hours"]))))

    if model.missing_tabs:
        findings.append(finding("check", "File", "Some course tabs were not found in this workbook",
                                "Missing: " + ", ".join(model.missing_tabs) +
                                ". Make sure you are uploading the A&S Planning Log and have not renamed the tabs."))

    # -- hours by course (current)
    for code in current:
        c = courses[code]
        label = f"{code} – {c['name']}"
        if c["logged"] >= c["target"]:
            findings.append(finding("ok", "Hours", f"{label}: hours target met",
                                    f"{_h(c['logged'])} of {_h(c['target'])} hours planned.", course=code))
        else:
            n_entries = int(-(-c["choice_remaining"] // prog["choice_max_per_activity"]))
            findings.append(finding(
                "action", "Hours", f"{label}: {_h(c['hours_remaining'])} more {'hour' if c['hours_remaining'] == 1 else 'hours'} needed",
                f"You have {_h(c['logged'])} of {_h(c['target'])} hours. Add about {n_entries} more CHOICE "
                f"{'entry' if n_entries == 1 else 'entries'} (each {_h(prog['choice_max_per_activity'])} hours or less).",
                course=code))
        if c["choice_logged"] > c["choice_needed"] + 0.01 and c["choice_needed"] > 0:
            findings.append(finding("tip", "Hours", f"{label}: more CHOICE hours than needed",
                                    f"You planned {_h(c['choice_logged'])} CHOICE hours; this course needs "
                                    f"{_h(c['choice_needed'])}. Extra hours can't be moved to other courses automatically, "
                                    "so check whether they belong in a later course's tab.", course=code))

    # -- row-level checks
    valid_roles, valid_locs = set(cfg["valid_roles"]), set(cfg["valid_locations"])
    max_choice = prog["choice_max_per_activity"]
    for code in active:
        tab = model.tabs[code]
        strict = status_of(code) == "current"
        sev = "action" if strict else "check"
        missing_items, bad_items, long_items, multi_items = [], [], [], []
        for a in tab.activities:
            where = f" on '{a.sheet}'" if a.sheet and a.sheet != code else ""
            tag = f"Row {a.row}{where} ({a.kind.title()})"
            miss = []
            if a.date is None:
                miss.append("date")
            if not a.location:
                miss.append("location")
            if strict:
                if not a.role:
                    miss.append("role")
                if a.kind == "CHOICE":
                    if not a.description or is_placeholder(a.description):
                        miss.append("a real description")
                    if a.hours <= 0:
                        miss.append("hours")
                    if not a.comps:
                        miss.append("a competency mark")
                elif not a.comps:
                    miss.append("a competency mark")
            if miss:
                missing_items.append(f"{tag}: add {', '.join(miss)}")
            if a.date_unreadable:
                bad_items.append(f"{tag}: the date could not be read. Use a format like 10/15/2026")
            if a.hours_unreadable:
                bad_items.append(f"{tag}: the hours value could not be read. Enter a number")
            if a.role and a.role not in valid_roles:
                bad_items.append(f"{tag}: role '{a.role}' is not one of {', '.join(sorted(valid_roles))}")
            if a.location and a.location not in valid_locs:
                bad_items.append(f"{tag}: location '{a.location}' is not in the dropdown list")
            if a.kind == "CHOICE" and a.hours > max_choice:
                long_items.append(f"{tag}: {_h(a.hours)} hours. Split it into entries of {_h(max_choice)} hours or less")
            if len(a.comps) > 1:
                multi_items.append(f"{tag}: {len(a.comps)} competencies marked. Mark ONE per activity")
        label = f"{code} – {courses[code]['name']}"
        if missing_items:
            why = ("These entries are incomplete." if strict else
                   "Missing dates or locations can keep hours from counting toward the external-hours requirement.")
            findings.append(finding(sev, "Missing details", f"{label}: {len(missing_items)} incomplete "
                                    f"{'entry' if len(missing_items) == 1 else 'entries'}", why, code, missing_items))
        if bad_items:
            findings.append(finding(sev, "Missing details", f"{label}: entries to correct", "", code, bad_items))
        if long_items:
            findings.append(finding(sev, "Hours", f"{label}: CHOICE activity over {_h(max_choice)} hours", "", code, long_items))
        if multi_items:
            findings.append(finding(sev, "Competencies", f"{label}: more than one competency marked",
                                    "Marked rows are left out of the competency totals until you choose one.", code, multi_items))

    # -- competencies
    short = [c for c in comp.values() if c["remaining"] > leeway]
    for c in comp.values():
        if c["remaining"] > 0 and c["min"] > 0:
            sev = "check" if c["remaining"] > leeway else "info"
            findings.append(finding(sev, "Competencies",
                                    f"Competency {c['n']} ({c['name']}): {_h(c['remaining'])} CHOICE hours still needed",
                                    f"Program minimum is {_h(c['min'])}; {_h(c['total'])} planned so far."))
        if c["excess"] > leeway:
            findings.append(finding("tip", "Competencies",
                                    f"Competency {c['n']} ({c['name']}): {_h(c['excess'])} hours above the minimum",
                                    "CHOICE hours are limited, so hours above a minimum leave less room for other competencies. "
                                    "A couple of hours either way is fine."))
    capacity = sum(courses[c]["choice_remaining"] for c in courses if status_of(c) != "completed")
    shortfall = sum(c["remaining"] for c in comp.values())
    if shortfall > capacity + leeway:
        findings.append(finding("check", "Competencies", "Competency minimums may not be reachable",
                                f"You still need {_h(shortfall)} CHOICE hours across competencies, but only "
                                f"about {_h(capacity)} CHOICE hours remain across your unfinished courses. "
                                "Rebalance future CHOICE entries toward the competencies you are short in."))

    # -- external locations
    short_types = [e["type"] for e in external["rows"] if e["min"] and e["remaining"] > 0]
    if external["total"] >= external["total_min"] and types_met >= external["types_needed"]:
        findings.append(finding("ok", "Locations", "External-location requirement met",
                                f"{_h(external['total'])} external hours across {types_met} site types."))
    else:
        if external["total"] < external["total_min"]:
            detail = (f"{_h(external['total'])} of {_h(external['total_min'])} external hours planned. ")
        else:
            detail = (f"Your {_h(external['total'])} external hours already cover the {_h(external['total_min'])}-hour total, "
                      "but the hours are not spread across enough site types. ")
        detail += (f"Site types still under {_h(minpt)} hours: {', '.join(short_types) or 'none'}. "
                   "'Main Site' (your own building) does not count as external.")
        findings.append(finding("check", "Locations", "External-location requirement not yet met", detail))
    if no_location > 0:
        findings.append(finding("check", "Locations", f"{_h(no_location)} hours have no usable location",
                                "Hours without a valid location can't count toward the external-hours requirement."))

    # -- duplicates (do not count) and copied Choice Library samples
    def tag_of(a, code):
        return f"Row {a.row}" + (f" on '{a.sheet}'" if a.sheet and a.sheet != code else "")

    def act_at(code, row):
        return next(x for x in model.tabs[code].activities if x.row == row)

    for reason in ("duplicate", "sample"):
        by_course = defaultdict(list)
        for (c, r), info in excluded.items():
            if info["reason"] == reason and status_of(c) != "future":
                by_course[c].append((r, info))
        for code, rows in by_course.items():
            items, lost = [], 0.0
            for r, info in sorted(rows):
                x = act_at(code, r)
                lost += x.hours
                if reason == "duplicate":
                    oc, orow = info["of"]
                    items.append(f"{tag_of(x, code)} repeats {oc} row {orow} ({round(info['score'] * 100)}% the same): "
                                 f"{_h(x.hours)} hours not counted")
                else:
                    items.append(f"{tag_of(x, code)} is copied from a Choice Library sample: {_h(x.hours)} hours not counted")
            n = len(rows)
            name = courses[code]["name"]
            sev = "action" if code in current else "check"
            if reason == "duplicate":
                findings.append(finding(sev, "Descriptions",
                                        f"{code} – {name}: {n} duplicate CHOICE {'entry' if n == 1 else 'entries'} not counted "
                                        f"({_h(lost)} hours)",
                                        "When two entries describe the same experience, only the first one (by date) counts toward "
                                        "your hours, competencies, and locations. Describe each experience in your own words, "
                                        "or delete the extra entry.", code, items))
            else:
                findings.append(finding(sev, "Descriptions",
                                        f"{code} – {name}: {n} CHOICE {'entry' if n == 1 else 'entries'} copied from the samples "
                                        f"not counted ({_h(lost)} hours)", "", code, items))

    for code in active:
        name = courses[code]["name"]
        is_current = code in current
        exact_i, contains_i, near_i, mismatch, quality = [], [], [], [], []
        for a in model.tabs[code].activities:
            key = (code, a.row)
            if a.kind != "CHOICE" or not a.description or is_placeholder(a.description) or key in excluded:
                continue
            tag = tag_of(a, code)
            f = lib_flags.get(key)
            if f:
                e = f["entry"]
                if f["kind"] == "exact":
                    exact_i.append(f"{tag}: copied from a Choice Library sample"
                                   + (f" (written for competency {e.comp})" if e and e.comp else ""))
                elif f["kind"] == "contains":
                    contains_i.append(f"{tag}: includes a Choice Library sample word-for-word. Make your own details the heart of the entry")
                else:
                    near_i.append(f"{tag}: {round(f['score'] * 100)}% the same as a Choice Library sample")
                if is_current and e and e.comp and len(a.comps) == 1 and a.comps[0] != e.comp:
                    mismatch.append(f"{tag}: the library wording is written for competency {e.comp}, "
                                    f"but you marked competency {a.comps[0]}")
            elif is_current:
                for h in quality_hints(a.description, a.role, th["min_words"]):
                    quality.append(f"{tag}: {h}")
        if exact_i:
            findings.append(finding("action" if is_current else "check", "Descriptions",
                                    f"{code} – {name}: copied from the Choice Library samples",
                                    "These match a sample entry. The samples are ideas, not entries. Rewrite each one in your own "
                                    "words: what you did, with whom, and what you will reflect on.", code, exact_i))
        if contains_i:
            findings.append(finding("check", "Descriptions", f"{code} – {name}: contain Choice Library wording",
                                    "A sample is pasted inside a longer description. Your own details should lead.", code, contains_i))
        if near_i and is_current:
            findings.append(finding("check", "Descriptions", f"{code} – {name}: very close to the Choice Library samples",
                                    "Only a few words differ from a sample. Describe your specific experience, your role, and "
                                    "what you will reflect on.", code, near_i))
        if mismatch:
            findings.append(finding("check", "Competencies", f"{code} – {name}: competency mark may not match the text",
                                    "", code, mismatch))
        if quality:
            findings.append(finding("tip", "Descriptions", f"{code} – {name}: ways to strengthen descriptions",
                                    "", code, quality))

    findings.sort(key=lambda f: SEV_ORDER[f["severity"]])

    # ---- instructor-only notes about the template itself
    template_notes = []
    for code, c in courses.items():
        s = c["sheet_choice_needed"]
        if s is not None and abs(s - c["choice_needed"]) > 0.01:
            template_notes.append(f"{code}: tab header says {_h(s)} CHOICE hours needed; a {_h(c['target'])}-hour "
                                  f"target with {_h(c['fixed'])} embedded/aligned hours implies {_h(c['choice_needed'])}.")

    return {
        "term": {"name": term_name, "year": term_year, "start": t_start, "end": t_end},
        "today": today, "pathway": pathway, "pathway_label": path_cfg.get("label", ""),
        "courses": courses, "competencies": list(comp.values()), "external": external,
        "totals": totals, "done": done, "findings": findings,
        "excluded": excluded, "lib_flags": lib_flags, "template_notes": template_notes,
        "model": model, "cfg": cfg, "library_index": lib,
    }
