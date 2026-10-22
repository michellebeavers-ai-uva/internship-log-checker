import os, sys, unittest
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.api import inspect_workbook, run
from engine.config import load_config, term_for_date, term_window
from engine.parse import read_workbook
from engine.rules import analyze
from engine.textcheck import similarity, is_placeholder

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample", "sample_student_workbook.xlsx")
TODAY = "2026-10-20"
STATUS = {"7806": "completed", "7812": "completed", "7808": "current", "7813": "current"}
ID = "S-48213"


class Terms(unittest.TestCase):
    def test_windows(self):
        cfg = load_config()
        self.assertEqual(term_for_date(cfg, date(2026, 10, 20)), ("Fall", 2026))
        self.assertEqual(term_for_date(cfg, date(2026, 12, 15)), ("Spring", 2027))   # crosses new year
        self.assertEqual(term_for_date(cfg, date(2027, 3, 1)), ("Spring", 2027))
        self.assertEqual(term_for_date(cfg, date(2026, 5, 2)), ("Summer", 2026))
        self.assertEqual(term_window(cfg, "Spring", 2027), (date(2026, 12, 2), date(2027, 5, 1)))

    def test_requirements(self):
        cfg = load_config()
        self.assertEqual(cfg["program"]["total_hours"], 320)
        self.assertEqual(len(cfg["courses"]) * cfg["program"]["course_target"], 320)
        self.assertEqual(cfg["courses"]["7805"]["name"], "Cultivating Professional Capacity")


class Text(unittest.TestCase):
    def test_similarity_and_placeholder(self):
        self.assertGreater(similarity("Lead a data meeting (VDOE 1d,3i)", "lead a data meeting"), 0.9)
        self.assertTrue(is_placeholder("Copy and paste choice hours here. No activity may be more than three hours"))
        self.assertTrue(is_placeholder("test"))
        self.assertFalse(is_placeholder("Facilitated a staff meeting on grading policy with the principal"))


class SampleMatching(unittest.TestCase):
    S = "Interview two school leaders about how they build a master schedule and write a summary of the tradeoffs they weigh each year."

    def test_kinds(self):
        from engine.textcheck import library_relation as rel
        self.assertEqual(rel(self.S, self.S)[0], "exact")
        self.assertEqual(rel(self.S + " (VDOE 1d,3i)", self.S)[0], "exact")                      # pasted with the code
        self.assertEqual(rel("Interview two school leaders about how they build a master schedule and write a summary", self.S)[0], "exact")
        self.assertEqual(rel("At Oak Elementary I did this: " + self.S + " Then I debriefed with my mentor.", self.S)[0], "contains")
        self.assertEqual(rel("Interview two principals about how they build a master schedule and write a summary of the tradeoffs they weigh every year.", self.S)[0], "near")
        self.assertIsNone(rel("Shadowed the transportation director during bus route planning and reflected on tradeoffs", self.S)[0])

    def test_contains_is_flagged_not_exact(self):
        model = read_workbook(SAMPLE, load_config())
        text = "At my school I did this: " + model.library[0].text + " Then I debriefed with my mentor."
        from engine.textcheck import LibraryIndex
        self.assertEqual(LibraryIndex(model.library).best_match(text)[0], "contains")


class Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = inspect_workbook(SAMPLE, "Fall", 2026, TODAY)
        cls.result, cls.docs = run(SAMPLE, "Fall", 2026, STATUS, "standard", ID, TODAY)

    def test_completed_column_detected(self):
        self.assertTrue(self.info["has_completed_column"])
        self.assertEqual(self.result["done"]["mode"], "column")

    def test_hours_math(self):
        c = self.result["courses"]["7808"]
        self.assertEqual((c["fixed"], c["choice_logged"], c["choice_needed"], c["logged"]), (25, 9, 7, 34))
        self.assertEqual(self.result["totals"]["target"], 320)

    def test_placeholders_are_not_duplicates(self):
        dup = [f for f in self.result["findings"] if "duplicate CHOICE" in f["title"]]
        self.assertEqual(len(dup), 1)
        self.assertIn("7813", dup[0]["title"])
        items = " | ".join(dup[0]["items"])
        self.assertIn("Row 10 repeats 7808 row 11", items)       # the earlier entry (7808) is the one that counts
        self.assertEqual(len(dup[0]["items"]), 1)                 # untouched placeholder rows are never duplicates
        # ...but each untouched placeholder is flagged once as needing a real description
        miss = [f for f in self.result["findings"] if "7808" in f["title"] and "incomplete" in f["title"]][0]
        self.assertTrue(any("Row 13" in i and "real description" in i for i in miss["items"]))

    def test_duplicates_do_not_count(self):
        ex = self.result["excluded"]
        self.assertEqual(ex[("7813", 10)]["of"], ("7808", 11))     # 7808 row 11 (10/8) is earlier than 7813 row 10 (11/20)
        self.assertNotIn(("7808", 11), ex)
        c = self.result["courses"]["7813"]
        self.assertEqual(c["choice_logged"], 1)                    # only row 12 (1 h) counts; the 2 h duplicate does not
        self.assertEqual(c["logged"], c["fixed"] + 1)
        comp = {x["n"]: x for x in self.result["competencies"]}
        self.assertEqual(comp[5]["current"], 3)                    # 7808 row 11 (3 h) counts; the 2 h repeat on 7813 does not

    def test_sample_copy_is_flagged_and_still_counts(self):
        flag = self.result["lib_flags"][("7813", 12)]
        self.assertEqual(flag["kind"], "exact")
        titles = [f["title"] for f in self.result["findings"] if f["severity"] == "action"]
        self.assertTrue(any("copied from the Choice Library samples" in t and "7813" in t for t in titles))
        self.assertNotIn(("7813", 12), self.result["excluded"])    # flagged, but its hour still counts by default
        self.assertEqual(self.result["courses"]["7813"]["choice_logged"], 1)

    def test_sample_copy_can_be_made_not_to_count(self):
        cfg = load_config(); cfg["text"]["count_library_copies"] = False
        model = read_workbook(SAMPLE, cfg)
        r = analyze(model, cfg, "Fall", 2026, STATUS, date(2026, 10, 20))
        self.assertEqual(r["excluded"][("7813", 12)]["reason"], "sample")
        self.assertEqual(r["courses"]["7813"]["choice_logged"], 0)

    def test_flags_expected_problems(self):
        t = [f["title"] for f in self.result["findings"]]
        self.assertTrue(any("over 3 hours" in x for x in t))

    def test_done_hours_current_previous_cumulative(self):
        h = self.result["done"]["hours"]
        # current: 7808 = 15+5 (rows 6,7) + 2 + 3 = 25 ; 7813 = 20+5 = 25  -> 50
        self.assertEqual(h["current"], 50)
        self.assertEqual(h["previous"], 29 + 34)          # every hour in finished courses
        self.assertEqual(h["cumulative"], 113)
        c = self.result["courses"]["7808"]
        self.assertEqual((c["done_hours"], c["not_done_hours"]), (25, 9))

    def test_competency_buckets(self):
        d = self.result["done"]["competency"]
        self.assertEqual((d[3]["current"], d[5]["current"], d[6]["current"]), (2, 3, 0))   # row 12 not completed
        self.assertEqual((d[3]["previous"], d[4]["previous"], d[5]["previous"]), (6, 6, 6))

    def test_external_excludes_main_site(self):
        ext = self.result["done"]["external"]
        self.assertEqual(ext["Agency"]["previous"], 20)
        self.assertNotIn("Main Site", ext)
        self.assertEqual(ext["Elementary"]["current"], 2)

    def test_fallback_without_completed_column(self):
        cfg = load_config()
        model = read_workbook(SAMPLE, cfg)
        model.has_completed_column = False
        r = analyze(model, cfg, "Fall", 2026, STATUS, date(2026, 10, 20))
        self.assertEqual(r["done"]["mode"], "date")
        # date rule: 7813 row 10 (11/20) is future; 7808 row 8 and placeholder rows have no date
        self.assertEqual(r["courses"]["7813"]["done_hours"], 30)

    def test_reports(self):
        for k in ("feedback", "start", "end"):
            self.assertIn("<html", self.docs[k])
            self.assertIn(f"Student ID: {ID}", self.docs[k])
        end = self.docs["end"]
        self.assertNotIn("Copy and paste choice hours", end)       # untouched placeholders stay off reports
        self.assertNotIn("Copy and paste choice hours", self.docs["start"])
        for word in ("This semester", "Previous", "Cumulative", "320 minimum"):
            self.assertIn(word, end)
        # start report: current enrollment only
        start = self.docs["start"]
        self.assertIn("7808", start); self.assertIn("7813", start)
        self.assertNotIn("7806 – School &amp; Community Relations", start)
        self.assertNotIn("Previously completed", start)

    def test_name_cell_never_reaches_reports(self):
        for k, html in self.docs.items():
            self.assertNotIn("Pat Example", html)
            self.assertNotIn("Invented Elementary", html)


class PageFiles(unittest.TestCase):
    def test_every_file_the_page_downloads_exists(self):
        import re
        root = os.path.join(os.path.dirname(__file__), "..")
        html = open(os.path.join(root, "index.html"), encoding="utf-8").read()
        engine = re.search(r"ENGINE_FILES = \[(.*?)\]", html, re.S).group(1)
        wheels = re.search(r"WHEELS = \[(.*?)\]", html, re.S).group(1)
        names = [("engine", n) for n in re.findall(r'"([^"]+)"', engine)] + [("wheels", n) for n in re.findall(r'"([^"]+)"', wheels)]
        self.assertGreaterEqual(len(names), 10)
        for folder, n in names:
            self.assertTrue(os.path.isfile(os.path.join(root, folder, n)), f"{folder}/{n} is listed in index.html but missing")
        self.assertNotIn("loadPackage", html)            # openpyxl is not in Pyodide's package list; it must ship as wheels


SAMPLE2 = os.path.join(os.path.dirname(__file__), "..", "sample", "sample_2nd_med_workbook.xlsx")
STATUS2 = {"7806": "completed", "7812": "completed", "7807": "completed", "7811": "completed",
           "7805": "current", "7810": "current", "7140": "current"}


class Pathways(unittest.TestCase):
    def test_every_course_appears_once_in_each_pathway(self):
        cfg = load_config()
        for key, n_sems in (("standard", 5), ("second_med", 4)):
            p = cfg["pathways"][key]
            self.assertEqual(len(p["semesters"]), n_sems)
            codes = [c for cs in p["semesters"].values() for c in cs] + p["experience_only"]   # experience-only blocks have no semester
            self.assertEqual(sorted(codes), sorted(cfg["courses"]), key)
        eo = cfg["pathways"]["second_med"]["experience_only"]
        self.assertEqual(sorted(eo), ["7140", "7813"])
        self.assertEqual(cfg["pathways"]["standard"]["experience_only"], [])

    def test_marker_is_detected_and_standard_log_is_not_marked(self):
        self.assertEqual(inspect_workbook(SAMPLE2, "Fall", 2026, TODAY)["detected_pathway"], "second_med")
        self.assertEqual(inspect_workbook(SAMPLE, "Fall", 2026, TODAY)["detected_pathway"], "standard")

    def test_second_med_run_auto_detects_and_labels_blocks(self):
        result, docs = run(SAMPLE2, "Fall", 2026, STATUS2, "auto", ID, TODAY)
        self.assertEqual(result["pathway"], "second_med")
        self.assertIn("(experiences only)", result["courses"]["7140"]["name"])
        self.assertNotIn("(experiences only)", result["courses"]["7805"]["name"])
        titles = [f["title"] for f in result["findings"]]
        self.assertIn("Reminder for 2nd-MEd students", titles)
        for k in ("feedback", "start", "end"):
            self.assertIn("2nd MEd (4 semesters)", docs[k])
        self.assertIn("7140 – Leadership II (LEAD II) (experiences only)", docs["end"].replace("&amp;", "&"))

    def test_experience_only_hours_count_like_any_course(self):
        result, _ = run(SAMPLE2, "Fall", 2026, STATUS2, "auto", ID, TODAY)
        c = result["courses"]["7140"]
        self.assertEqual((c["fixed"], c["choice_needed"], c["choice_logged"], c["logged"]), (30, 2, 2, 32))
        self.assertEqual(c["done_hours"], 32)
        # 7140 hours land in the cumulative totals and in the external-hours table
        self.assertEqual(result["done"]["external"]["Central Office"]["current"], 25)
        self.assertEqual(result["done"]["competency"][3]["current"], 3 + 2)       # 7805 row + 7140 row

    def test_no_reminder_when_block_is_not_current(self):
        st = dict(STATUS2, **{"7140": "future"})
        result, _ = run(SAMPLE2, "Fall", 2026, st, "auto", ID, TODAY)
        self.assertNotIn("Reminder for 2nd-MEd students", [f["title"] for f in result["findings"]])

    def test_explicit_standard_overrides_marker(self):
        result, _ = run(SAMPLE2, "Fall", 2026, STATUS2, "standard", ID, TODAY)
        self.assertNotIn("(experiences only)", result["courses"]["7140"]["name"])

    def test_combined_tab_is_read_as_two_courses(self):
        info = inspect_workbook(SAMPLE2, "Fall", 2026, TODAY)
        self.assertEqual(info["missing_tabs"], [])                      # 7140 / 7813 have no tabs of their own
        model = read_workbook(SAMPLE2, load_config())
        fixed = lambda code: [a for a in model.tabs[code].activities if a.kind != "CHOICE"]
        self.assertEqual(len(fixed("7140")), 2)                         # embedded + aligned
        self.assertEqual(len(fixed("7813")), 3)                         # embedded + two aligned
        self.assertEqual({a.sheet for a in model.tabs["7140"].activities}, {"2nd Int Addl Reqs"})
        self.assertEqual(model.tabs["7140"].sheet_choice_needed, 2)

    def test_messages_name_the_combined_tab(self):
        st = dict(STATUS2, **{"7813": "current"})                       # 7813 block is still empty: dates, roles missing
        result, _ = run(SAMPLE2, "Fall", 2026, st, "auto", ID, TODAY)
        miss = [f for f in result["findings"] if "7813" in f["title"] and "incomplete" in f["title"]][0]
        self.assertTrue(all("on '2nd Int Addl Reqs'" in i for i in miss["items"]))

    def test_second_med_log_has_completed_column_and_320_total(self):
        info = inspect_workbook(SAMPLE2, "Fall", 2026, TODAY)
        self.assertTrue(info["has_completed_column"])
        self.assertEqual(info["missing_tabs"], [])
        self.assertEqual(len(info["courses"]), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
