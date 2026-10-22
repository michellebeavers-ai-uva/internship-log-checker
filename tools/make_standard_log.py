"""Build the standard (5-semester) A&S Planning Log: Completed column + the shared formula fixes.

  python tools/make_standard_log.py "A_S_Planning_Log.xlsx" "A_S_Planning_Log_Standard.xlsx"
"""
import json
import os
import sys
import tempfile

from openpyxl import load_workbook

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tools.add_completed_column import add_column  # noqa: E402
from tools.log_fixes import apply_common_fixes, assert_no_array_formulas, build_all_choice  # noqa: E402

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engine", "requirements.json"), encoding="utf-8"))
ORDER = ["7806", "7812", "7811", "7807", "7810", "7140", "7808", "7805", "7813", "7815"]
NAMES = {c: v["name"] for c, v in CFG["courses"].items()}


def build(src, dst):
    tmp = os.path.join(tempfile.mkdtemp(), "t.xlsx")
    add_column(src, tmp)
    wb = load_workbook(tmp)
    apply_common_fixes(wb, ORDER)
    colors = {"7806": "2E7D32", "7812": "2E7D32", "7811": "0000FF", "7807": "0000FF", "7810": "9900FF", "7140": "9900FF",
              "7808": "FF00FF", "7805": "FF00FF", "7813": "FF0000", "7815": "FF0000"}          # the template's tab colors
    build_all_choice(wb, [(c, f"{c} – {NAMES[c]}", 6, 59) for c in ORDER], colors)
    assert_no_array_formulas(wb)
    wb.calculation.fullCalcOnLoad = True
    wb.save(dst)
    return dst


if __name__ == "__main__":
    print("wrote", build(sys.argv[1], sys.argv[2]))
