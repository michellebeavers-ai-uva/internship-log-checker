"""Build the 2nd MEd (4-semester) version of the A&S Planning Log from the standard template.

  python tools/make_second_med_log.py "A_S_Planning_Log.xlsx" "A_S_Planning_Log_2nd_MEd.xlsx"

2nd MEd students do not take 7140 or 7813, but they still complete those internship experiences. This script:
  * removes the 7140 and 7813 tabs and adds ONE tab, "2nd Int Addl Reqs", holding both requirements (64 hours)
  * colors the course tabs by 2nd-MEd semester (green, blue, purple, magenta); the new tab is teal
  * orders the tabs by semester and shows the 4-semester sequence on Home
  * repoints every formula that used the removed tabs (Dashboard and the All CHOICE tab)
  * adds the Completed column (tools/add_completed_column.py)
Formula fixes (each carries a cell comment):
  (shared with the standard log: tools/log_fixes.py)
  * 7807 counted a 35-hour target; now 32 like every other course (320 total)
  * Dashboard competency totals use SUMIFS (the original SUMPRODUCT/IFERROR formulas show #VALUE! in Excel), start at
    row 6 on every tab, and Competency 3 no longer repeats the High-school location formula
  * All CHOICE competency totals always read 0 (shifted columns); they now link to the Dashboard totals
  * All CHOICE listing rebuilt with plain formulas (see tools/log_fixes.py) so it works in Excel and Google Sheets
"""
import json
import os
import re
import sys
import tempfile
from copy import copy

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools.add_completed_column import add_column  # noqa: E402
from tools.log_fixes import apply_common_fixes, assert_no_array_formulas, build_all_choice  # noqa: E402

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engine", "requirements.json"), encoding="utf-8"))
PATH = CFG["pathways"]["second_med"]
NAMES = {c: v["name"] for c, v in CFG["courses"].items()}
BLOCKS = PATH["experience_only"]                         # ["7140", "7813"]: no tab of their own any more
SEM = {code: int(n) for n, codes in PATH["semesters"].items() for code in codes if code not in BLOCKS}
SEM_COLOR = {1: "FF2E7D32", 2: "FF0000FF", 3: "FF9900FF", 4: "FFFF00FF"}   # the template's colors for semesters 1-4
SEM_COLOR_NAME = {1: "Green tabs", 2: "Blue tabs", 3: "Purple tabs", 4: "Magenta tabs"}
NEW_TAB = "2nd Int Addl Reqs"                            # no apostrophe: it would have to be doubled in every formula
NEW_COLOR = "FF00838F"                                   # teal: used by no other tab
TAB_ORDER = ["🏠 Home", "7806", "7812", "7811", "7807", "7810", "7805", "7808", "7815", NEW_TAB,
             "📊 Dashboard", "All CHOICE", "📚 Competencies", "⭐ Choice Library-All Aligned",
             "⭐ Choice Library-By Course if y", "📓 Journals", "CHOICE calc"]
BLOCK_TARGET, CHOICE_ROWS = 32, 5
TEAL = PatternFill("solid", fgColor=NEW_COLOR)
INPUT = PatternFill("solid", fgColor="FFFFFDE7")


def copy_style(src, dst):
    dst._style = copy(src._style)


def note(cell, text):
    cell.comment = Comment(text, "2nd MEd log")


def copy_row(src, r_src, dst, r_dst, values=True, last_col=26):
    for c in range(1, last_col + 1):
        s, d = src.cell(r_src, c), dst.cell(r_dst, c)
        copy_style(s, d)
        if values:
            d.value = s.value
    dst.row_dimensions[r_dst].height = src.row_dimensions[r_src].height


def first_row(ws, text_start):
    return next(r for r in range(1, ws.max_row + 1) if str(ws.cell(r, 1).value or "").startswith(text_start))


# ------------------------------------------------------------------ the new tab
def build_tab(wb):
    src1, src2 = wb["7140"], wb["7813"]
    ws = wb.create_sheet(NEW_TAB)
    ws.sheet_properties.tabColor = NEW_COLOR
    ws.freeze_panes = "A6"
    for key, dim in src1.column_dimensions.items():
        nd = ws.column_dimensions[key]
        nd.min, nd.max, nd.width = dim.min, dim.max, dim.width

    # rows 1-5: same header rows as every course tab
    for r in range(1, 6):
        copy_row(src1, r, ws, r)
    for rng in ("A1:M1", "A2:D2", "E2:F2", "H2:I2", "A3:F3", "A4:M4"):
        ws.merge_cells(rng)
    ws["A1"].value = "INTERNSHIP LOG  |  2nd MEd Internship Additional Requirements  |  7140 + 7813 experiences"
    ws["A4"].value = ("You do not take 7140 or 7813 in the 2nd MEd program, but you still complete their internship experiences "
                      "(32 hours each, 64 in all). They count toward your 320 hours, competency minimums, and location "
                      "requirements. Plan each block with your supervisor.")
    ws["A4"].font = Font(name="Calibri", size=10, italic=True, color="FF7F6000")
    ws["A4"].fill = PatternFill("solid", fgColor="FFFFF2CC")
    ws["A4"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[4].height = 36
    ws["J2"].value = "=(64-G2)"
    note(ws["J2"], "Two blocks of 32 hours (7140 and 7813).")
    data_rows, sem_cells = [], []
    row = 6
    out = {}
    for code, src in (("7140", src1), ("7813", src2)):
        choice_band_src = first_row(src, "⭐")
        ea_src = [r for r in range(6, choice_band_src)]
        # --- block band
        band = row
        for c in range(1, 16):
            cell = ws.cell(band, c)
            cell.fill = TEAL
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFFFF")
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.merge_cells(start_row=band, start_column=1, end_row=band, end_column=4)
        ws.cell(band, 1).value = f"{code} – {NAMES[code]}  |  {BLOCK_TARGET} hours"
        ws.row_dimensions[band].height = 30
        # --- semester row
        sem = band + 1
        ws.merge_cells(start_row=sem, start_column=1, end_row=sem, end_column=4)
        ws.cell(sem, 1).value = "Semester you will complete this block:"
        ws.cell(sem, 1).font = Font(name="Calibri", size=10, bold=True, color="FF1B2A4A")
        ws.cell(sem, 1).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(sem, 5).fill = INPUT
        ws.cell(sem, 5).font = Font(name="Calibri", size=10, bold=True, color="FF1B2A4A")
        ws.cell(sem, 5).alignment = Alignment(vertical="center")
        ws.row_dimensions[sem].height = 22
        sem_cells.append(ws.cell(sem, 5).coordinate)
        # --- embedded / aligned rows, copied from the old tab
        r = sem + 1
        e1 = r
        for rs in ea_src:
            copy_row(src, rs, ws, r)
            data_rows.append(r)
            r += 1
        # --- choice band + rows
        cband = r
        copy_row(src, choice_band_src, ws, cband)
        ws.merge_cells(start_row=cband, start_column=1, end_row=cband, end_column=4)
        ws.merge_cells(start_row=cband, start_column=5, end_row=cband, end_column=6)
        ws.cell(cband, 1).value = f"⭐  CHOICE HOURS  —  2 hours needed for {code}"
        c1, cl = cband + 1, cband + CHOICE_ROWS
        ws.cell(cband, 5).value = (f'=IF(SUMIF(A{c1}:A{cl},"CHOICE",F{c1}:F{cl})>=2,"✅ Choice Hours Met!",'
                                   f'"⚠ Still need: "&(2-SUMIF(A{c1}:A{cl},"CHOICE",F{c1}:F{cl}))&" more hours")')
        for k in range(CHOICE_ROWS):
            copy_row(src, choice_band_src + 1, ws, c1 + k)
            ws.cell(c1 + k, 1).value = "CHOICE"
            data_rows.append(c1 + k)
        # --- block status line (text only: no numbers in column F, so tab totals are not double counted)
        tot = f"SUM(F{e1}:F{cl})"
        ws.cell(band, 5).value = (f'=IF({tot}>={BLOCK_TARGET},"✅ "&{tot}&" of {BLOCK_TARGET} hours: target met",'
                                  f'"⚠ "&{tot}&" of {BLOCK_TARGET} hours: "&({BLOCK_TARGET}-{tot})&" more needed")')
        out[code] = {"band": band, "first": e1, "last": cl, "sum": f"SUM('{NEW_TAB}'!F{e1}:F{cl})"}
        row = cl + 2                                           # one blank row between blocks

    # validations (same lists as the course tabs) + Completed + semester pickers
    cols = {"Role": 4, "Location": 3, "Completed": 15}
    for label, col in cols.items():
        f1 = {"Role": '"Observer,Participant,Leader"',
              "Location": '"Main Site,Elementary,Middle,High,Central Office,Agency,Other"',
              "Completed": '"Yes"'}[label]
        dv = DataValidation(type="list", formula1=f1, allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv)
        for r in data_rows:
            dv.add(ws.cell(r, col))
    dv = DataValidation(type="list", formula1='"Semester 1,Semester 2,Semester 3,Semester 4"', allow_blank=True)
    ws.add_data_validation(dv)
    for ref in sem_cells:
        dv.add(ref)
    return out


# ------------------------------------------------------------------ main
def build(src_path, dst_path):
    tmp = os.path.join(tempfile.mkdtemp(), "t.xlsx")
    add_column(src_path, tmp)
    wb = load_workbook(tmp)
    blocks = build_tab(wb)
    course_tabs = [c for c in NAMES if c not in BLOCKS]

    # ---------- Home
    h = wb["🏠 Home"]
    h["A1"].value = "A&S Internship Program  |  Planning Log  |  2nd MEd Pathway"
    h["A2"].value = "Pathway: 2nd MEd (4 semesters)"
    h["A2"].font = Font(name="Calibri", size=11, bold=True, color="FF1B2A4A")
    h["A2"].alignment = Alignment(vertical="center")
    h.row_dimensions[2].height = 22
    h["B14"].value = (h["B14"].value.rstrip() + f" You also complete the experiences on the '{NEW_TAB}' tab (the 7140 and "
                      "7813 requirements). You do not take those two courses.")
    h.row_dimensions[14].height = 46
    h["C21"].value = "Tab color"
    h["C21"].font = Font(name="Calibri", size=11, bold=True, color="FFFFFFFF")
    for n in range(1, 5):
        r = 21 + n
        courses = [c for c in PATH["semesters"][str(n)] if c not in BLOCKS]
        h.cell(r, 1).value = f"Semester {n}"
        if n == 3 and h.cell(r, 1).fill.fill_type is None:
            copy_style(h["A25"], h.cell(r, 1))
        h.cell(r, 2).value = "   |   ".join(f"{c} – {NAMES[c]}" for c in courses)
        h.cell(r, 3).value = SEM_COLOR_NAME[n]
        h.cell(r, 3).fill = PatternFill("solid", fgColor=SEM_COLOR[n])
        h.cell(r, 3).font = Font(name="Calibri", size=10, bold=True, color="FFFFFFFF")
    h["A26"].value = "Also required"
    h["B26"].value = (f"'{NEW_TAB}' tab: the internship experiences for 7140 (Leadership II) and 7813 (Educational "
                      "Technology), 32 hours each. You do not take these courses, but you complete their experiences. "
                      "Plan them with your supervisor.")
    h["B26"].alignment = Alignment(wrap_text=True, vertical="center")
    h["C26"].value = "Teal tab"
    h["C26"].fill = TEAL
    h["C26"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFFFF")
    h.row_dimensions[26].height = 44
    h["B27"].fill = PatternFill(fill_type=None)           # stray grey cell left over from the "Semester 5" row

    # ---------- course tabs: semester number in the title, tab color by semester
    for code in course_tabs:
        ws = wb[code]
        m = re.match(r"(INTERNSHIP LOG\s*\|\s*)(.+?)(\s*\|\s*Semester\s*)\d+", str(ws["A1"].value))
        ws["A1"].value = f"{m.group(1)}{m.group(2)}{m.group(3)}{SEM[code]}"
        ws.sheet_properties.tabColor = SEM_COLOR[SEM[code]]

    # ---------- Dashboard
    d = wb["📊 Dashboard"]
    d["A3"].value = d["A3"].value.replace("5 semesters", "4 semesters")
    rows = {str(d.cell(r, 1).value)[:4]: r for r in range(5, 15)}
    for code in BLOCKS:
        r = rows[code]
        d.cell(r, 1).value = f"{code} – {NAMES[code]} experiences ({NEW_TAB} tab)"
        d.cell(r, 2).value = "=" + blocks[code]["sum"]
    tabs = course_tabs + [NEW_TAB]
    apply_common_fixes(wb, tabs)
    for r, loc in zip(range(33, 39), ["Elementary", "Middle", "High", "Central Office", "Agency", "Other"]):
        d.cell(r, 2).value = "=" + "+".join(
            f"IFERROR(SUMIF('{t}'!C6:C200,\"{loc}\",('{t}'!F6:F200)),0)" for t in tabs)

    # ---------- All CHOICE (Google Sheets formula) and the removed tabs
    sources = [(t, f"{t} – {NAMES[t]}", 6, 59) for t in course_tabs]
    sources += [(NEW_TAB, f"{c} – {NAMES[c]}", blocks[c]["band"], blocks[c]["last"]) for c in BLOCKS]
    colors = {c: SEM_COLOR[SEM[c]][2:] for c in course_tabs}
    colors.update({c: NEW_COLOR[2:] for c in BLOCKS})
    build_all_choice(wb, sources, colors)
    del wb["7140"]
    del wb["7813"]

    # ---------- tab order (by semester) and tab colors
    wb._sheets = [wb[name] for name in TAB_ORDER]
    wb.active = 0
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "🏠 Home"
    assert_no_array_formulas(wb)
    wb.calculation.fullCalcOnLoad = True
    wb.save(dst_path)
    return dst_path


if __name__ == "__main__":
    print("wrote", build(sys.argv[1], sys.argv[2]))
