# A&S Internship Planning-Log Checker

**New to GitHub? Start with `SETUP_GUIDE.md`.**

Students open a web page, choose their own A&S Planning Log (.xlsx), and get:

- **Feedback**: hours by course, CHOICE hours by competency, external-location hours, incomplete entries,
  repeated or copied descriptions, and suggestions for stronger descriptions.
- **Start-of-semester plan** and **End-of-semester summary** (Summer 5/2–8/1, Fall 8/2–12/1, Spring 12/2–5/1),
  each showing what was completed in earlier courses.

**No AI and no accounts.** All checks are fixed rules in Python (`engine/`). The file is read inside the
student's browser (Pyodide) and is never uploaded. Claude is only needed by *you*, to maintain the code.

## What students do

1. Open the page, choose their planning log, and type a **Student ID** (printed on reports instead of a name).
2. Answer two questions: **Which courses are you currently enrolled in?** and **Which courses have you already completed?**
3. Get three documents they can print or download:
   - **Feedback** on the whole plan (hours, competencies, locations, incomplete or repeated entries, descriptions).
   - **Start-of-semester plan**: the courses they are enrolled in now, their planned hours and experiences, open items.
   - **End-of-semester summary**: hours for **this semester**, **previous courses**, and the **cumulative** total against the
     320-hour minimum, plus competency and external-location hours in the same three columns.

The workbook's **Name** cell and the file name are never read, so names cannot appear on a report.

## Layout

```
index.html                the student page (loads Python into the browser)
engine/requirements.json  ALL program numbers: targets, competency minimums, external hours, terms
wheels/                   openpyxl + et_xmlfile (pure Python, MIT) loaded by the page; Pyodide does not provide openpyxl
engine/*.py               parse.py (read workbook) - rules.py (checks) - textcheck.py - reports.py - api.py
cli.py                    run the same checks from VS Code / a terminal
tools/add_completed_column.py   adds a "Completed" dropdown column to a copy of the template
tools/make_standard_log.py      builds the standard log (Completed column + formula fixes)
tools/make_second_med_log.py    builds the 2nd MEd (4-semester) log with the combined 2nd Int Addl Reqs tab
tools/log_fixes.py              formula fixes and the All CHOICE rebuild shared by both builders
SETUP_GUIDE.md                  step-by-step GitHub + Canvas setup for beginners
sample/                   a synthetic workbook (invented data) to try it with
tests/                    python tests/test_engine.py
```

## The Completed column

Students asked to track what they have finished. `tools/add_completed_column.py` adds a **Completed** column (dropdown: Yes)
to every course tab of a *copy* of your template:

```
python tools/add_completed_column.py "A_S_Planning_Log.xlsx" "A_S_Planning_Log_with_Completed.xlsx"
```
Open the copy in Excel and compare it with your original before sharing. The checker finds the column by its header text.

- **With the column:** an activity in a current course counts as completed only when marked Yes.
- **Without it (older logs):** an activity counts as completed when its date is on or before today. The page tells the student which rule applied.
- **Courses a student lists as completed** count every hour entered in those tabs.

## What counts, and what gets flagged

- **Duplicate entries do not count.** If two CHOICE descriptions are the same (90% similar or more), the **earliest by date counts**
  and later repeats count for nothing: not course hours, competencies, locations, or the program total. The report lists them with
  their hours crossed out and a "Not counted" tag. (Undated entries sort after dated ones.) Setting: `text.duplicate_similarity`.
- **Copied samples are flagged.** Each CHOICE entry is compared with every Choice Library sample (and the log's own sample text).
  *Copied from a sample* (identical, or a pasted piece of one) is a "fix now" item; *contains sample wording* (a sample plus extra
  words) and *very close* (85%+ the same) are "check" items. Settings: `text.library_similarity`, `text.exact_similarity`.
  Copied entries still count by default; set `text.count_library_copies` to `false` in `engine/requirements.json` if they should not.
- The Excel **Dashboard** in the log adds up every entry it can see. It does not know about duplicates, so its totals can be higher than
  the checker's reports. The reports are the ones that exclude repeats.

## Report branding

Reports use the UVA brand palette (UVA Blue #232D4B, UVA Orange #E57200, light gray #F1F1EF) and a text header. Edit the
`branding` section of `engine/requirements.json` to change the words. The official UVA logo files are not included; add them
through the University brand site if you need the logo itself.

## The 2nd MEd pathway

2nd MEd students do not take **7140** or **7813**, but they still complete those internship experiences, so they finish all
320 hours in four semesters. In the 2nd MEd log those two requirements live together on one tab, **2nd Int Addl Reqs**
(teal), in two blocks of 32 hours. Each block has a **Semester** dropdown the student sets. The four semesters of courses are
color-coded (green, blue, purple, magenta).

```
python tools/make_second_med_log.py "A_S_Planning_Log.xlsx" "A_S_Planning_Log_2nd_MEd.xlsx"
python tools/make_standard_log.py   "A_S_Planning_Log.xlsx" "A_S_Planning_Log_Standard.xlsx"
```
The Home tab carries a line "Pathway: 2nd MEd (4 semesters)". **The checker reads that line**, preselects the pathway, labels
7140 and 7813 "(experiences only)", reads each block of the combined tab as its own course, and asks "Which courses or
experience-only blocks are you working on this semester?". Experience-only hours count exactly like course hours in every total.
Messages about those rows say "on '2nd Int Addl Reqs'" so the student knows where to look.

Both builders apply the same fixes (see `tools/log_fixes.py`): the Dashboard competency totals use `SUMIFS` (the original
`SUMPRODUCT/IFERROR` formulas show `#VALUE!` in Excel), the 7807 target is 32 hours, the total target is 320, leftover test data
is cleared, the external-hours message checks the per-site-type minimum, and **All CHOICE** is rebuilt with plain formulas
(hidden helper sheet `CHOICE calc`) so it works in Excel and Google Sheets.

## Run it in VS Code

```
pip install -r requirements.txt     # (python3 -m pip install openpyxl on a Mac)
python cli.py sample/sample_student_workbook.xlsx --term Fall --year 2026 --current 7808,7813 --completed 7806,7812 --student-id S-48213 --out reports
python tests/test_engine.py
```
`--pathway` defaults to `auto` (reads the log's Home tab); use `standard` or `second_med` to override.
The CLI also prints "template notes" (places where the workbook's own numbers disagree) for you.

## Publish for students (GitHub Pages) and embed in Canvas

1. Push this folder to a GitHub repo.
2. Settings > Pages > Deploy from branch > `main` / root. Your page is `https://<account>.github.io/<repo>/`.
3. **Canvas iframe:** ask your Canvas admin to allow `<account>.github.io` for embedded content (Canvas restricts which
   domains can be iframed in course pages), then embed the URL in a page. GitHub Pages does not block framing.
   If printing or downloading is blocked inside the frame, the page shows an "Open in its own tab" link.

The *code* on GitHub Pages is public; student data never reaches GitHub because it stays in the browser.
Do not commit real student workbooks to the repo.

## Test the browser layer once (5 minutes)

The Python engine and the page's own logic are tested here, but the page loads Pyodide from the jsDelivr CDN, which
could not be reached from the build environment. Open the Pages URL (or run `python -m http.server` in this folder and
visit localhost:8000), choose `sample/sample_student_workbook.xlsx`, enter an ID, select 7808 and 7813 as current and
7806 and 7812 as completed, and confirm the three reports appear. First load takes 10-20 seconds.

## Changing requirements

Edit `engine/requirements.json` (targets, minimums, valid roles/locations, term dates, similarity thresholds) and re-run
the tests. No code changes needed for those.

## Assumptions to confirm

- **Embedded experiences for 7140 and 7813** are left as written. They are normally assigned by a course instructor, which these
  students don't have, so decide how they are assigned and submitted.
- **Course target is 32 hours** for every course, so the program minimum is 320 (the Dashboard's 326 comes from the 7807 and 7140 tabs using 35).
- **External hours:** every site type must reach 12.5 hours *and* the total must reach 50, as in the Dashboard
  (`external_types_needed: 5`). Set it to 4 if the intent is "any four of the five".
- A CHOICE row with more than one competency mark is left out of competency totals until fixed.
