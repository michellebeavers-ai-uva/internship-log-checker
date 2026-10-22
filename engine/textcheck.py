"""Plain-Python text checks: similarity, library matching, description quality. No AI, no network."""
import re
from difflib import SequenceMatcher

PLACEHOLDER_PATTERNS = [
    r"copy and paste choice hours here",
    r"no activity may be more than three hours",
]
JUNK = {"test", "asdf", "tbd", "n/a", "na", "xxx", "todo", "none"}

STRONG_VERBS = {
    "analyze", "analyse", "lead", "facilitate", "design", "develop", "create", "plan", "present",
    "evaluate", "conduct", "draft", "organize", "coordinate", "implement", "review", "audit",
    "compare", "build", "write", "propose", "recommend", "monitor", "mentor", "coach", "negotiate",
    "advocate", "model", "apply", "assess", "prepare", "revise", "summarize", "synthesize",
    "interview", "survey", "co-lead", "manage", "produce",
}
WEAK_ONLY = {"observe", "attend", "shadow", "sit", "listen", "watch", "learn", "help", "assist", "see"}
LEAD_VERBS = {"lead", "facilitate", "design", "develop", "plan", "present", "organize", "co-lead", "run", "chair"}
OUTCOME_WORDS = {
    "report", "plan", "reflection", "reflect", "summary", "analysis", "recommendations",
    "recommendation", "notes", "presentation", "proposal", "journal", "artifact", "memo",
    "debrief", "findings", "feedback", "agenda", "rubric", "timeline", "draft", "outline",
}
PEOPLE_WORDS = {
    "teacher", "teachers", "staff", "principal", "principals", "team", "teams", "committee",
    "students", "families", "parents", "board", "superintendent", "counselor", "counselors",
    "coach", "coaches", "administrator", "administrators", "leaders", "leader", "faculty",
    "community", "stakeholders", "mentor", "department", "director", "assistant",
}


def norm(text):
    t = text.lower()
    t = re.sub(r"\(vdoe[^)]*\)", " ", t)          # library codes like (VDOE 1d,3i)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text):
    return set(norm(text).split())


def similarity(a, b):
    """0..1. Containment of a long phrase counts as an exact copy."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 40 and short in long_:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def is_placeholder(text):
    n = norm(text)
    if not n:
        return False
    if n in JUNK or len(n) < 4:
        return True
    return any(re.search(p, n) for p in PLACEHOLDER_PATTERNS)


def library_relation(student, sample, near=0.85, exact=0.98):
    """How a student's text relates to a Choice Library sample.

    -> (kind, score). kind is one of:
       'exact'    the same words (or the student pasted a piece of the sample)
       'contains' the whole sample appears inside a longer student text (sample + the student's additions)
       'near'     very similar wording
       None       different
    """
    ns, nl = norm(student), norm(sample)
    if not ns or not nl:
        return None, 0.0
    if ns == nl:
        return "exact", 1.0
    ratio = SequenceMatcher(None, ns, nl).ratio()
    if ratio >= exact:
        return "exact", ratio
    if len(ns) >= 40 and ns in nl:                 # a pasted fragment of the sample
        return "exact", 1.0
    if len(nl) >= 40 and nl in ns:                 # the sample plus more words
        return "contains", 1.0
    if ratio >= near:
        return "near", ratio
    return None, ratio


_RANK = {"exact": 3, "contains": 2, "near": 1, None: 0}


class LibraryIndex:
    def __init__(self, entries):
        self.entries = [(e, tokens(e.text)) for e in entries]

    def best_match(self, text, near=0.85, exact=0.98):
        """-> (kind, score, entry) for the closest sample; kind is None when nothing is close."""
        tk = tokens(text)
        best = (None, 0.0, None)
        if not tk:
            return best
        for e, etk in self.entries:
            union = len(tk | etk)
            overlap = len(tk & etk) / union if union else 0
            short, long_ = (tk, etk) if len(tk) <= len(etk) else (etk, tk)
            covered = len(short & long_) / len(short) if short else 0
            if overlap < 0.4 and covered < 0.9:            # cheap pre-filter
                continue
            kind, score = library_relation(text, e.text, near, exact)
            if (_RANK[kind], score) > (_RANK[best[0]], best[1]):
                best = (kind, score, e)
        return best


def duplicate_score(na, nb, threshold):
    """Similarity of two already-normalized texts, or 0.0 if they are clearly below `threshold` (cheap early exits)."""
    if not na or not nb:
        return 0.0
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 40 and short in long_:
        return 1.0
    sm = SequenceMatcher(None, na, nb)
    if sm.real_quick_ratio() < threshold or sm.quick_ratio() < threshold:
        return 0.0
    return sm.ratio()


def duplicate_pairs(items, threshold):
    """items: list of (key, text). Returns [(key_a, key_b, score)] at/above threshold."""
    out = []
    normed = [(k, norm(t), t) for k, t in items]
    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            ka, na, ta = normed[i]
            kb, nb, tb = normed[j]
            if not na or not nb:
                continue
            s = similarity(ta, tb)
            if s >= threshold:
                out.append((ka, kb, s))
    return out


def quality_hints(description, role, min_words):
    """Friendly, rule-based suggestions for improving a description. Returns a list of strings."""
    words = norm(description).split()
    hints = []
    if len(words) < min_words:
        hints.append(f"Add detail: this is {len(words)} words. Aim for at least {min_words}, "
                     "covering what you will do, with whom, and what you will produce or reflect on.")
    wordset = set(words)
    has_strong = bool(wordset & STRONG_VERBS)
    if not has_strong and (wordset & WEAK_ONLY):
        hints.append("This describes watching or helping rather than leading a task. Add an action you take "
                     "(analyze, facilitate, draft, present, debrief...) so the experience shows leadership practice.")
    if not (wordset & OUTCOME_WORDS):
        hints.append("Name what you will produce or reflect on (a summary, plan, reflection, recommendations, notes...).")
    if not (wordset & PEOPLE_WORDS) and len(words) >= 4:
        hints.append("Say who is involved (for example a principal, grade-level team, committee, or families).")
    r = (role or "").lower()
    if r == "observer" and wordset & LEAD_VERBS and not (wordset & {"observe", "shadow"}):
        hints.append("Your role is Observer, but the description sounds like you lead the work. Check that the role matches.")
    if r == "leader" and wordset & {"observe", "shadow", "attend"} and not (wordset & LEAD_VERBS):
        hints.append("Your role is Leader, but the description sounds like observation. Check that the role matches.")
    return hints[:3]
