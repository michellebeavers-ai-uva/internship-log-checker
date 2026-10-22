# Setup guide: from your computer to your students (no GitHub experience needed)

**What you are building:** a web page that students open, choose their planning log on their own computer, and get feedback
and reports. The page runs entirely in the student's browser. Their file is never uploaded anywhere, and nobody needs a
Claude account.

**What GitHub is, in one paragraph:** a free website that stores a folder of files and can also *host* a web page made from
those files (this feature is called **GitHub Pages**). You only need three ideas:
a **repository** (a folder on GitHub), a **commit** (saving a change; GitHub keeps every version), and
**Pages** (the switch that turns the folder into a website).

---

## Part 1. Test it on your own computer first

You will need the folder unzipped. If the zip won't download from the Claude desktop app, open claude.ai in Safari or Chrome
and download from there. **Double-click the zip to unzip it** (on a Mac this makes a folder called `intern-checker`).

### 1a. Run the automatic tests (2 minutes)

1. Open **VS Code**. Choose **File > Open Folder** and pick the `intern-checker` folder.
2. Open the terminal: **Terminal > New Terminal**.
3. Type each line, then press Return:

```
python3 -m pip install openpyxl
python3 tests/test_engine.py
```

On Windows use `python` instead of `python3`.

**You should see** a list of test names, each ending in `ok`, and finally `Ran 22 tests` and `OK`.
If you see `FAILED` or `Error`, stop and send me the last 15 lines of the terminal.

### 1b. Run the web page on your own computer (5 minutes)

1. In the same terminal, type: `python3 -m http.server 8000` and press Return. (Leave it running.)
2. Open your browser and go to **http://localhost:8000**
3. The page should appear. The first time you choose a file it takes **10-20 seconds** while it loads its engine; that is normal.
   This step needs an internet connection.
   **Check the address bar:** it must say `localhost:8000`. If it says `file:///...`, you opened the file by double-clicking it;
   close that tab and type the address instead. The page cannot work from a double-click.
4. Run the two checks in **Part 4** below, then go back to the terminal and press **Control + C** to stop.

---

## Part 2. Put it on GitHub

### 2a. Create your account (5 minutes)

1. Go to **github.com** and choose **Sign up**. Use your work email if you like.
2. **Pick your username carefully.** It becomes part of your students' web address
   (`https://YOURNAME.github.io/...`). Something professional and neutral works well.
3. Verify your email when GitHub asks.
4. Recommended: **Settings > Emails** and tick **Keep my email addresses private**. Also turn on two-factor
   sign-in under **Settings > Password and authentication**.

### 2b. Create a repository (the folder on GitHub)

1. Click the **+** at the top right, then **New repository**.
2. **Repository name:** `internship-log-checker` (no spaces; this also becomes part of the web address).
3. Choose **Public**. (Free accounts need Public to use Pages. See the privacy note below; student data is never stored there.)
4. Tick **Add a README file**, then click **Create repository**.

### 2c. Upload the files

1. On your new repository page click **Add file > Upload files**.
2. On your computer, open the unzipped `intern-checker` folder. **Select everything *inside* it** (`index.html`, `engine`, `tests`,
   and the rest; press Command-A on a Mac) and **drag it into the GitHub page**.
   - Do **not** drag the `intern-checker` folder itself, and do not drag the zip. GitHub will not unzip it, and an extra
     folder would change your web address.
3. Wait until every file shows a progress bar finishing. Scroll down and click **Commit changes**.

**Checkpoint:** the repository page should now list `engine`, `sample`, `tests`, `tools`, `index.html`, `README.md` and others,
with `index.html` directly in the list (not inside another folder). Click the `engine` folder: it must contain
`api.py`, `config.py`, `parse.py`, `reports.py`, `requirements.json`, `rules.py`, `textcheck.py`, `__init__.py`.
Click the `wheels` folder: it must contain two files ending in `.whl` (`et_xmlfile...` and `openpyxl...`). These are the small
spreadsheet-reading files the page needs; they are not available from anywhere else.

### 2d. Turn on GitHub Pages (the switch that makes it a website)

1. In your repository click the **Settings** tab (top row, far right).
2. In the left sidebar click **Pages**.
3. Under **Build and deployment**, set **Source** to **Deploy from a branch**. Under **Branch** choose **main** and
   **/ (root)**, then click **Save**.
4. Wait 1-3 minutes and refresh the page. A box appears: **Your site is live at https://YOURNAME.github.io/internship-log-checker/**.
   That link is the one you give to students. **Write it down.**

---

## Part 3. Put it in Canvas

**Easiest (works for everyone):** edit a Canvas page, highlight some text such as "Check your planning log", click the
**link** icon, choose **External URL**, paste your link, and save.

**Embedded on the page (your preference):** Canvas only allows embedding from approved websites. Ask your Canvas administrator
to add `YOURNAME.github.io` to the allowed list for embedded content, then use **Embed** or the HTML editor with:

```html
<iframe src="https://YOURNAME.github.io/internship-log-checker/" width="100%" height="900" title="Planning log checker"></iframe>
```

If printing or downloading is blocked inside the frame, the page shows an **Open this page in its own tab** link.

### Message to paste for students

> **Check your planning log (optional, private).** Open the link below, choose your A&S Planning Log, enter your **Student ID**
> (not your name), and tell it which courses you are in this semester. You will get feedback and a start- and end-of-semester
> report you can download or print. Your file stays on your computer; nothing is uploaded.
> **If you work in Google Sheets:** first choose **File > Download > Microsoft Excel (.xlsx)** and choose that downloaded file.
> The first time can take about 20 seconds to load.

---

## Part 4. Test with the sample files (do this twice: on your computer in 1b, and again on the real GitHub link)

The sample files contain **invented** data. Open the page and:

**Check A: standard log**
1. Choose `sample/sample_student_workbook.xlsx`.
2. Student ID: `TEST-1`. Semester **Fall**, year **2026**. Program should show **Standard (5 semesters)**.
3. Currently enrolled: **7808** and **7813**. Already completed: **7806** and **7812**. Click **Check my log**.
4. **You should see:** `6 to fix now`, `5 to check`, `2 tips`, `1 already met`. Under *End of semester*, hours should read
   **50 this semester, 63 previous, 113 cumulative** against the 320 minimum.
5. **Look for the two new checks.** In *Feedback*, find *"7813 – Educational Technology: 1 duplicate CHOICE entry not counted
   (2 hours)"* (it repeats an earlier entry in 7808) and *"7813 – ...: copied from the Choice Library samples"*. In *End of
   semester*, the 7813 table shows the repeated entry's hours crossed out with a **Not counted** tag, and the last entry tagged
   **Copied from a sample**. The report has the UVA School of Education header in UVA Blue and Orange.

**Check B: 2nd MEd log**
1. Choose `sample/sample_2nd_med_workbook.xlsx`.
2. The program should **switch to 2nd MEd (4 semesters) by itself**, and 7140 and 7813 should say *(experiences only)*.
3. Currently: **7805, 7810, 7140**. Completed: **7806, 7812, 7807, 7811**. Student ID `TEST-2`. Click **Check my log**.
4. **You should see:** `2 to fix now`, `7 to check`, `0 tips`, `1 already met`. End of semester: **60 this semester, 100 previous,
   160 cumulative**.

**Check C: your real blank logs.** Choose `A_S_Planning_Log_Standard.xlsx` and `A_S_Planning_Log_2nd_MEd.xlsx` in turn (not a student's
file), with 7806 and 7812 as currently enrolled and nothing completed. Both should show `4 to fix now`, `7 to check`, `0 tips`,
`0 already met`. That is correct for an empty log.

If any number differs, take a screenshot and send it to me.

---

## Part 5. Changing things later

- **Replace a file:** open the repository, click **Add file > Upload files**, drag in the new version (same file name), and
  **Commit changes**. Wait 1-2 minutes, then reload the web page with **Command-Shift-R** (Windows: Ctrl-Shift-R).
- **Change a requirement** (for example a competency minimum or a term date): in the repository open `engine`, click
  `requirements.json`, click the **pencil** icon, edit, and **Commit changes**.
- **Undo a mistake:** every change is saved. Click the **clock** icon / **History** on a file to see and restore earlier versions.

## Troubleshooting

| What you see | What to try |
|---|---|
| **404** on your link | Pages can take up to 10 minutes the first time. Check Settings > Pages shows "live", the repository is **Public**, and `index.html` is at the top level of the file list. |
| Page loads but says *Could not start the checker* | The `engine` or `wheels` folder is missing or incomplete (see the checkpoint in 2c), or the network blocks `cdn.jsdelivr.net`. Try a different network or device. |
| *Could not read this file as the A&S Planning Log* | The student chose a different file, or a Google Sheet that was never downloaded as .xlsx. |
| A tab was *not found* | The student renamed or deleted a course tab. |
| Old version still showing | Hard reload (Command-Shift-R), or wait a minute. |
| Embedded page is blank in Canvas | The domain is not on Canvas's allowed list yet. Use the plain link until it is. |

## Privacy, in plain terms

- **Public repository** means anyone can read the *code* and the sample files (which are invented). That is normal and fine.
- **Student data never reaches GitHub.** A student's workbook is read inside their own browser and never uploaded.
  Reports are created in their browser and saved or printed by the student, who chooses whether to submit them.
- The page asks for a **Student ID**, never a name, and the tool ignores the Name cell and file name in the workbook.
- **Never** upload a real student workbook or report to the repository.
- Your account name appears in the web address. Use a neutral one.
