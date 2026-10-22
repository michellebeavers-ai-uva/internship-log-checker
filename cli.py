"""Run the checker from VS Code / a terminal.

  python cli.py path/to/log.xlsx --out reports
  python cli.py log.xlsx --term Fall --year 2026 --current 7808,7813 --pathway second_med --student-id 12345
"""
import argparse
import os

from engine.api import inspect_workbook, run


def main():
    p = argparse.ArgumentParser(description="A&S Internship planning-log checker")
    p.add_argument("workbook")
    p.add_argument("--term", choices=["Summer", "Fall", "Spring"])
    p.add_argument("--year", type=int, help="Year the term ends in (Spring 2027 = Dec 2026 - May 2027)")
    p.add_argument("--current", help="Comma-separated course codes taken this term (overrides auto-detect)")
    p.add_argument("--completed", help="Comma-separated course codes finished in earlier terms")
    p.add_argument("--pathway", choices=["auto", "standard", "second_med"], default="auto",
                   help="auto reads the pathway marker on the log's Home tab")
    p.add_argument("--student-id", default="", help="ID to print on the reports (never a name)")
    p.add_argument("--today", help="YYYY-MM-DD (for testing)")
    p.add_argument("--out", default="reports")
    a = p.parse_args()

    info = inspect_workbook(a.workbook, a.term, a.year, a.today)
    statuses = {c["code"]: c["status"] for c in info["courses"]}
    if a.current or a.completed:
        statuses = {k: "future" for k in statuses}
        for code in (a.completed or "").split(","):
            if code.strip():
                statuses[code.strip()] = "completed"
        for code in (a.current or "").split(","):
            if code.strip():
                statuses[code.strip()] = "current"

    result, docs = run(a.workbook, a.term, a.year, statuses, a.pathway, a.student_id, a.today)
    os.makedirs(a.out, exist_ok=True)
    for name, html in docs.items():
        path = os.path.join(a.out, f"{name}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("wrote", path)
    t = info
    print(f"Term: {t['term']} {t['year']}  |  current: {[c for c, s in statuses.items() if s == 'current']}")
    for f in result["findings"]:
        if f["severity"] in ("action", "check"):
            print(f"  [{f['severity']}] {f['title']}")
    if result["template_notes"]:
        print("\nTemplate notes (for the instructor):")
        for n in result["template_notes"]:
            print("  -", n)


if __name__ == "__main__":
    main()
