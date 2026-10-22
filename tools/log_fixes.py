"""Formula fixes shared by the standard and 2nd MEd logs.

Why: the template's Dashboard competency totals used SUMPRODUCT(IFERROR(1*range,0), ...). Google Sheets and LibreOffice
evaluate that as an array; Excel does not, and shows #VALUE!. SUMIFS gives the same answer in Excel, Google Sheets and
LibreOffice, with no array evaluation.
"""
from openpyxl.comments import Comment


def note(cell, text):
    cell.comment = Comment(text, "Planning log")


def competency_formula(tabs, col):
    """CHOICE hours marked X in competency column `col`, summed over `tabs` (rows 6-200 of each tab)."""
    return "=" + "+".join(
        f"SUMIFS('{t}'!$F$6:$F$200,'{t}'!$A$6:$A$200,\"CHOICE\",'{t}'!{col}$6:{col}$200,\"X\")" for t in tabs)


def clear_test_entries(wb, tabs):
    """The original template still held someone's test data in CHOICE rows (7806: 'test', 5 hours; 7811: a stray X).
    Clear every student-input cell (columns B-O) of every CHOICE row so a new log starts clean."""
    cleared = []
    for t in tabs:
        ws = wb[t]
        for r in range(6, ws.max_row + 1):
            if str(ws.cell(r, 1).value or "").strip().upper() != "CHOICE":
                continue
            for c in range(2, 16):
                if ws.cell(r, c).value not in (None, ""):
                    cleared.append(f"{t}!{ws.cell(r, c).coordinate}")
                    ws.cell(r, c).value = None
    return cleared


def apply_common_fixes(wb, tabs):
    clear_test_entries(wb, tabs)
    # 1. 7807 / 7140 tabs counted a 35-hour target; every other course uses 32 (10 x 32 = 320)
    for t in tabs:
        ws = wb[t]
        if ws["J2"].value == "=(35-G2)":
            ws["J2"].value = "=(32-G2)"
            note(ws["J2"], "Target changed from 35 to 32 hours so all courses total 320.")
            for r in range(6, 12):
                v = ws.cell(r, 1).value
                if isinstance(v, str) and v.startswith("⭐"):
                    ws.cell(r, 1).value = v.replace("5 hours needed", "2 hours needed")

    d = wb["📊 Dashboard"]
    # 2. total target is the sum of the course targets (the original typed 326)
    d["C15"].value = "=SUM(C5:C14)"
    note(d["C15"], "Total target is the sum of the course targets (320). The original was typed as 326.")

    # 3. competency totals: SUMIFS instead of SUMPRODUCT(IFERROR(...)); counts from row 6 on every tab
    for i, col in enumerate("GHIJKL"):
        d.cell(19 + i, 2).value = competency_formula(tabs, col)
    note(d["B19"], "Competency totals now use SUMIFS (works in Excel and Google Sheets; the old SUMPRODUCT/IFERROR "
                   "formulas showed #VALUE! in Excel), read from row 6 on every tab (the first CHOICE row on 7807/7140 "
                   "was skipped), and Competency 3 no longer repeats the High-school location formula.")

    # 3b. the external-hours total said "Requirement Met!" even while individual site types still needed hours
    d["D39"].value = ('=IF(B39>=50,IF(COUNTIF(B33:B37,"<12.5")=0,"✅ Requirement Met!",'
                      '"✅ 50-hr total met, but "&COUNTIF(B33:B37,"<12.5")&" site type(s) are under 12.5 hrs"),'
                      '"⚠ "&TEXT(MAX(0,50-B39),"0")&" more external hrs needed")')
    note(d["D39"], "Now also checks the 12.5-hour minimum for each site type, so it no longer says 'Met' while a site type is short.")

    # 4. All CHOICE cumulative competency hours read the wrong columns (always 0): link to the Dashboard
    a = wb["All CHOICE"]
    for i in range(6):
        a.cell(8 + i, 11).value = f"='📊 Dashboard'!B{19 + i}"
    note(a["K8"], "These totals always showed 0 (they read the wrong columns). Now linked to the Dashboard.")


def assert_no_array_formulas(wb):
    bad = [f"{ws.title}!{c.coordinate}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
           if isinstance(c.value, str) and c.value.startswith("=") and "SUMPRODUCT" in c.value.upper()]
    assert not bad, f"SUMPRODUCT still present: {bad}"


# ----------------------------------------------------------------------------------------------------------------------
# All CHOICE: plain formulas that work in Excel (any version) and Google Sheets.
# The template's version used QUERY/LAMBDA/VSTACK (Google Sheets only), skipped any choice row without a date, and only
# read rows 10-20 of each tab. This version uses a hidden helper sheet with one row per possible choice row.
# ----------------------------------------------------------------------------------------------------------------------
CALC = "CHOICE calc"
FIRST_ROW, LAST_ROW = 6, 139          # All CHOICE rows 6-139 (the template's own G1 total covers G6:G139)


def build_all_choice(wb, sources, course_colors=None):
    """sources: [(tab name, course label, first source row, last source row), ...] in the order they should be listed.
    course_colors: {course code: "RRGGBB"} used to color column A by the course's semester (the tab colors)."""
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill

    calc = wb.create_sheet(CALC)
    calc.sheet_state = "hidden"
    calc.sheet_properties.tabColor = "FF555555"
    heads = ["Course", "Tab", "Row", "Entry?", "Seq", "Competency", "Date", "Site name", "Site type",
             "Experience", "Role", "Hours"]
    for c, h in enumerate(heads, 1):
        calc.cell(1, c).value = h
    calc["N1"].value = ("Helper sheet for All CHOICE: one row per possible CHOICE row on the course tabs. "
                        "A row counts as an entry when it has a description or hours. Do not edit.")
    r = 2
    for tab, label, first, last in sources:
        q = f"'{tab}'!"
        for src in range(first, last + 1):
            calc.cell(r, 1).value = label
            calc.cell(r, 2).value = tab
            calc.cell(r, 3).value = src
            calc.cell(r, 4).value = (f'=IF(AND(UPPER(TRIM({q}A{src}))="CHOICE",LEN(TRIM({q}E{src}&{q}F{src}))>0),1,0)')
            calc.cell(r, 5).value = f'=IF(D{r}=1,MAX(E$1:E{r - 1})+1,"")'
            calc.cell(r, 6).value = (f'=IF(D{r}=1,IFERROR(CHOOSE(MATCH("X",{q}G{src}:L{src},0),'
                                     f'"①","②","③","④","⑤","⑥"),""),"")')
            calc.cell(r, 7).value = f'=IF(D{r}=1,IF({q}B{src}="","",{q}B{src}),"")'
            calc.cell(r, 8).value = f'=IF(D{r}=1,{q}N{src}&"","")'
            calc.cell(r, 9).value = f'=IF(D{r}=1,{q}C{src}&"","")'
            calc.cell(r, 10).value = f'=IF(D{r}=1,{q}E{src}&"","")'
            calc.cell(r, 11).value = f'=IF(D{r}=1,{q}D{src}&"","")'
            calc.cell(r, 12).value = f'=IF(D{r}=1,IF({q}F{src}="","",{q}F{src}),"")'
            r += 1
    last = r - 1

    a = wb["All CHOICE"]
    # All CHOICE column <- helper column.  Competency, Date, Name the Location, Type, Experience, Role, Hours, Course
    mapping = {1: "F", 2: "G", 3: "H", 4: "I", 5: "J", 6: "K", 7: "L", 8: "A"}
    for row in range(FIRST_ROW, LAST_ROW + 1):
        k = f"ROWS(A${FIRST_ROW}:A{row})"
        for col, src in mapping.items():
            a.cell(row, col).value = (f"=IFERROR(INDEX('{CALC}'!${src}$2:${src}${last},"
                                      f"MATCH({k},'{CALC}'!$E$2:$E${last},0)),\"\")")
        a.cell(row, 2).number_format = "m/d/yyyy"
    a["H5"].value = "Course"
    a["H5"].font = a["G5"].font.copy()
    a["H5"].alignment = a["G5"].alignment.copy()
    a["A3"].value = (f"=MAX('{CALC}'!$E$2:$E${last})&\" CHOICE entries found on your course tabs. A row is listed when it has a \"&"
                     f"\"description or hours.\"&IF(MAX('{CALC}'!$E$2:$E${last})>{LAST_ROW - FIRST_ROW + 1},"
                     f"\"  WARNING: only the first {LAST_ROW - FIRST_ROW + 1} are shown.\",\"\")")
    a["A3"].font = Font(name="Calibri", size=10, italic=True, color="FFFFFFFF")     # the band behind it is dark navy
    a["A3"].alignment = Alignment(wrap_text=True, vertical="center")
    a.column_dimensions["H"].width = 38
    from copy import copy
    for col in range(2, 9):                      # the template styles row 6 differently from the rows below it
        a.cell(FIRST_ROW, col)._style = copy(a.cell(FIRST_ROW + 1, col)._style)
    a.cell(FIRST_ROW, 2).number_format = "m/d/yyyy"
    a.row_dimensions[FIRST_ROW].height = a.row_dimensions[FIRST_ROW + 1].height
    # column A: the old fixed color strip no longer lines up with a compact list; color by the course's semester instead
    base = PatternFill("solid", fgColor="FFFFE599")
    for row in range(FIRST_ROW, LAST_ROW + 1):
        a.cell(row, 1).fill = base
        a.cell(row, 1).font = Font(name="Calibri", size=11, bold=True, color="FF1B2A4A")
        a.cell(row, 1).alignment = Alignment(horizontal="center", vertical="center")
    by_color = {}
    for code, color in (course_colors or {}).items():
        by_color.setdefault(color, []).append(code)
    for color, codes in by_color.items():
        cond = "OR(" + ",".join(f'LEFT($H{FIRST_ROW},4)="{c}"' for c in codes) + ")"
        a.conditional_formatting.add(f"A{FIRST_ROW}:A{LAST_ROW}", FormulaRule(
            formula=[cond], stopIfTrue=False,
            fill=PatternFill(start_color=color, end_color=color, fill_type="solid"),
            font=Font(color="FFFFFFFF", bold=True)))
    note(a["A6"], "Rebuilt with plain formulas (works in Excel and Google Sheets). Lists every CHOICE row that has a "
                  "description or hours, in tab order. Name the Location = the tab's Site name; Type = the tab's Location.")
    return last
