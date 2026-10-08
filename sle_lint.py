#!/usr/bin/env python3
"""sle_lint.py: lint for LS-SLE 2026-10-08 (LawSnap Simplified Legal English).

Flags the mechanical rules in the LS-SLE rulebook (README.md in this repo).
Judgment rules (S1, S3, S4, P1, P9, P11, I2, I3, I6, and most of the structure layer) stay manual.
P12b (Dale-Chall) runs only if the optional `textstat` package is installed.
https://github.com/LawSnap/ls-sle  ·  MIT License (see LICENSE-CODE).

Usage:
    python3 sle_lint.py FILE [FILE ...] --profile published|internal

Exit code 1 if any FAIL. WARN never fails the run.
Text inside double quotes is exempt (quoted sources are not yours to edit).
Text between <!-- sle-off --> and <!-- sle-on --> is skipped (for example, a list of banned words).
"""
import argparse
import os
import re
import sys

# ---------------------------------------------------------------- rule data

# (rule, severity, regex, message). Checked against quote-masked text.
SHARED = [
    ("S2", "FAIL", r"—|(?<=\w) -- (?=\w)|(?<=\w)--(?=\w)| – ",
     "dash: use a period, comma, colon, or parentheses"),
]

PUBLISHED = [
    ("P2", "FAIL",
     r"\b(isn['’]t|is not|wasn['’]t|was not|aren['’]t|are not)\b[^.!?]{0,80}?(—|–|--|;|,)\s*(it['’]s|it is|it was|this is|that['’]s|they['’]re)\b",
     "contrast-reversal (isn't X, it's Y): state Y"),
    ("P2", "FAIL",
     r"\b(didn['’]t|doesn['’]t|don['’]t|isn['’]t|wasn['’]t) just\b",
     "contrast-reversal (didn't just X, it Y): state both facts plainly"),
    ("P2", "FAIL",
     r"\b(isn['’]t|is not|wasn['’]t|was not)\s+(the\s+)?(question|point|issue|problem|story|answer)\b",
     "contrast-reversal (X isn't the question, Y is): state Y"),
    ("P3", "FAIL", r"(^|[.!?*]\s+)Not\b",
     "sentence starts with 'Not' (Not X. Y.): state Y"),
    ("P13", "WARN", r"(?i)^#\s.*(\bwe (read|reviewed|coded|analyzed|looked at)\b|\b\d[\d,]*\s+(rulings|claims|cases|motions|requests|decisions|orders)\b)",
     "headline carries the sample size: move 'we read N' to the sub-line or lede"),
    ("P4", "FAIL", r"(?i)\briver\b[^.!?]{0,80}\b(feet|foot|deep|depth)\b|\baverage depth\b",
     "river-depth metaphor (retired): state the counts, 'Overall, X of Y. In [subgroup], Z of W.'"),
    ("H3B", "WARN", r"(?i)^#{2,3}\s+(?!where the average misleads)[^\n]*\baverage\b",
     "exception heading: use exactly 'Where the average misleads' (subtitle after a colon)"),
    ("P4", "FAIL",
     r"\b(nobody|no one) (warns|tells|talks about|mentions)\b|\bthe (trap|secret|truth) (nobody|no one)\b|\bhere['’]s the (thing|kicker|catch|twist)\b|\bthe real (question|story|answer|reason)\b|\bplot twist\b|\bspoiler\b|\bgame[- ]changer\b",
     "hype label: cut it, let the fact carry the weight"),
    ("P3", "WARN", r"(?i)\bnot just\b",
     "'not just' (a common AI-writing tell): state the fact"),
    ("P5", "WARN", r"\bnot\b[^.!?]{0,40},\s*not\b",
     "negation stack (not X, not Y): say what it is"),
    ("P7", "WARN", r"\*\*\*[^*]+\*\*\*|\b[A-Z]{4,}(?:-[A-Za-z]+)?\b",
     "heavy emphasis (***x*** or CAPS): one emphasis per section max"),
]

# banned word -> replacement (published)
PUB_WORDS_FAIL = {
    r"leverag(e|es|ed|ing)": "use",
    r"utiliz(e|es|ed|ing)": "use",
    r"delv(e|es|ed|ing)|dive into": "look at",
    r"robust": "(cut)",
    r"landscape": "name the area",
    r"seamless(ly)?": "(cut)",
    r"unlock(s|ed|ing)?": "give / allow",
    r"empower(s|ed|ing)?": "(cut)",
    r"it['’]s worth noting( that)?": "(cut)",
    r"importantly": "(cut)",
    r"moreover|furthermore|additionally": "also",
    r"in sharp contrast|in stark contrast": "state both numbers side by side",
    r"testament to": "(cut)",
    r"myriad": "many (give the count)",
    r"at the end of the day": "(cut)",
    r"needless to say": "(cut)",
}
PUB_WORDS_WARN = {
    r"actually": "(cut, except once in a headline)",
    r"really|truly|genuinely": "(cut)",
    r"simply|plainly|clearly|obviously": "(cut)",
    r"crucial|critical": "(cut, or say why; legal 'critical' is fine)",
    r"navigat(e|es|ed|ing)": "handle (if figurative)",
}

INTERNAL = [
    ("I1", "WARN", r"\b(and then|then also|and also)\b",
     "possible two instructions in one sentence: split"),
]
INT_WORDS_FAIL = {
    r"ready": "name the exact state from your glossary",
    r"etc\.?": "list every item",
    r"and/or": "'or', 'and', or 'X, Y, or both'",
    r"should": "'must' (required) or 'can' (optional)",
    r"ASAP|soon|later": "a date (YYYY-MM-DD)",
}
INT_WORDS_WARN = {
    r"today|yesterday|tomorrow|next week|this week|last week": "absolute date (YYYY-MM-DD)",
    r"approved": "say what was approved, by whom (use your glossary term)",
    r"done": "name the end state",
}
# Glossary terms that contain a banned word are allowed. Add your own.
INT_ALLOW = [r"\bPUBLISHED\b"]

# Acronyms that are not emphasis. Add your own.
ACRONYMS = {"FAIL", "WARN", "INTERNAL", "PUBLISHED", "LICENSE", "CODE", "README", "MIT", "URL", "STE", "ASD", "SOP", "SOPS",
            "NOTE", "TODO", "ASAP", "HTTP", "HTML", "JSON", "YYYY", "ISO", "USA",
            "FAQ", "CEO", "LLC", "NASA", "LASC", "CACI", "PAGA", "FEHA", "CCPA",
            "CIPA", "RICO", "FDUTPA", "UCLA", "ERISA", "OSHA", "HIPAA", "FINRA",
            "CCP", "IIED", "CPRA"}

SENT_MAX = {"published": 45, "internal": 20}
STACCATO_WORDS, STACCATO_RUN = 6, 3  # P10: 3+ sentences in a row under 6 words
ABBREV = r"\b(v|Inc|Corp|Co|No|Cal|App|Supp|Cir|Dist|Ct|U\.S|e\.g|i\.e|Mr|Ms|Dr|St|vs|subd|Civ|Proc|Elec|Pac|Gov|Bus|Prof|Lab|Evid|Pen|Fam|Prob|Veh|Ins|Health|Saf)\."

# ---------------------------------------------------------------- helpers

def mask_quotes(line):
    """Replace double-quoted spans with a placeholder. Court words are exempt."""
    line = re.sub(r"“[^”]*”", '"…"', line)
    return re.sub(r'"[^"\n]*"', '"…"', line)


def word_rules(words, sev, rule):
    out = []
    for pat, repl in words.items():
        out.append((rule, sev, r"(?i)\b(" + pat + r")\b", f"banned word -> {repl}"))
    return out


def sentences(line):
    safe = re.sub(ABBREV, lambda m: m.group(0).replace(".", "§"), line)
    safe = re.sub(r"(\d)\.(\d)", r"\1§\2", safe)
    parts = re.split(r"(?:(?<=[.!?])|(?<=[.!?]\*)|(?<=[.!?]\*\*)|(?<=[.!?]\")|(?<=[.!?]\u201d))\s+(?=[A-Z*\"“(\[])", safe)
    return [p.replace("§", ".") for p in parts if p.strip()]


def strip_md(s):
    return re.sub(r"[*_`#>\[\]]", "", s)


# H6 (2026-10-07): group by the issue, not by the outcome.
ENABLE_H6 = True

# H6 candidate: a list holds items of one kind. Direction = the first outcome word in each item's label.
DENY_WORDS = r"denied|denial|denials|denies|overruled|survived|survives"
GRANT_WORDS = r"struck|strike|strikes|stricken|granted|grant|grants|sustained|dismissed|excluded"
ITEM_RE = re.compile(r"^\s*(\*\*.+?\*\*|\d+\.\s.*|[-*+]\s.*)")


def list_direction_check(lines):
    """WARN when one section's list items lead with opposite outcomes (deny vs. grant)."""
    out, items = [], []

    def flush():
        dirs = {d for _, d in items if d}
        unlabeled = [n for n, d in items if not d]
        # Narrow version: a mixed list is fine if every item's label states its outcome.
        if len(dirs) == 2 and unlabeled:
            lines_by = ", ".join(f"L{n}:{d}" for n, d in items if d)
            out.append((items[0][0], "WARN", "H6",
                        "list mixes outcome directions: group by issue, with losing and winning versions side by side (H6)",
                        lines_by))
        items.clear()

    for n, raw in enumerate(lines, 1):
        if raw.startswith("#"):
            flush()
            continue
        m = ITEM_RE.match(raw)
        if not m:
            continue
        label = m.group(1)
        bold = re.search(r"\*\*(.+?)\*\*", raw)  # the bold label, wherever it sits
        if bold:
            label = bold.group(1)
        label = mask_quotes(label)
        w = re.search(rf"(?i)\b({DENY_WORDS}|{GRANT_WORDS})\b", label)
        d = None
        if w:
            d = "deny" if re.fullmatch(rf"(?i){DENY_WORDS}", w.group(1)) else "grant"
        items.append((n, d))
    flush()
    return out


# P12b: Dale-Chall vocabulary backstop (WARN above DC_MAX). Needs textstat for the word list;
# skipped quietly if textstat is not installed. FK grade is reported, never gated.
DC_MAX = 7.9
TERMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terms-of-art.txt")


def _load_words():
    try:
        import textstat
    except ImportError:
        return None, None, None
    easy = set()
    with open(os.path.join(os.path.dirname(textstat.__file__), "resources", "en", "easy_words.txt")) as f:
        easy = {w.strip().lower() for w in f if w.strip()}
    terms = set()
    if os.path.exists(TERMS_FILE):
        with open(TERMS_FILE) as f:
            terms = {w.strip().lower() for w in f if w.strip() and not w.startswith("#")}
    return easy, terms, textstat


def _in(word, vocab):
    if word in vocab:
        return True
    for suf, rep in (("ies", "y"), ("es", ""), ("s", ""), ("ed", ""), ("ed", "e"), ("d", ""),
                     ("ing", ""), ("ing", "e"), ("ly", ""), ("er", ""), ("est", ""), ("'s", "")):
        if word.endswith(suf) and (word[: -len(suf)] + rep) in vocab:
            return True
    return False


def prose_lines(lines):
    """Prose only: no headings, tables, code, comments, quotes, case names, cites, links."""
    out, in_code, in_front, off = [], False, False, False
    for n, raw in enumerate(lines, 1):
        t = raw.strip()
        if n == 1 and t == "---":
            in_front = True
            continue
        if in_front:
            in_front = t != "---"
            continue
        if t.startswith("```"):
            in_code = not in_code
            continue
        if "<!-- sle-off -->" in raw:
            off = True
        if "<!-- sle-on -->" in raw:
            off = False
            continue
        if in_code or off or not t or t.startswith(("#", "|", "<!--", "---")):
            continue
        x = re.sub(r"\]\([^)]*\)", "]", raw)
        x = re.sub(r"https?://\S+|<[^>]+>", " ", x)
        x = re.sub(r'"[^"]*"|“[^”]*”', " ", x)                       # quoted court language
        x = re.sub(r"(?<![*\w])\*(?!\*)[^*]+?\*(?!\*)", " ", x)  # *Case Name*
        x = re.sub(r"§+\s*[\d.()a-z]+|\b\d+\s+Cal\.[^,;)]*|\bNo\.\s*\S+|\b\d[\d,./%-]*\b", " ", x)
        x = re.sub(r"[*_`>\[\]]|^\s*([-+]|\d+\.)\s+(\[ \]\s*)?", " ", x)
        out.append(x)
    return out


DC_MIN_WORDS = 80  # shorter blocks give unstable scores


def readability_blocks(lines):
    """[(line_no, heading, score)] for each '## ' block over DC_MAX with enough prose."""
    out, start, head = [], 0, "(top of piece)"
    bounds = [(i, l[3:].strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    marks = [(0, "(top of piece)")] + bounds + [(len(lines), None)]
    for (i, h), (j, _) in zip(marks, marks[1:]):
        r = readability(lines[i:j])
        if r and r[3] >= DC_MIN_WORDS and r[0] > DC_MAX:
            out.append((i + 1, h, r[0], r[3]))
    return out


def readability(lines):
    easy, terms, ts = _load_words()
    if easy is None:
        return None
    words = sents = hard_raw = hard = syll = 0
    for x in prose_lines(lines):
        for sent in sentences(x):
            toks = re.findall(r"[A-Za-z][A-Za-z'-]*[A-Za-z]|[A-Za-z]", sent)
            toks = [t for t in toks if len(t) > 1 or t.lower() in ("a", "i")]
            if not toks:
                continue
            sents += 1
            for i, t in enumerate(toks):
                w = t.lower()
                words += 1
                syll += ts.syllable_count(w)
                if i > 0 and t[0].isupper():   # proper noun: familiar by convention
                    continue
                if sum(c.isupper() for c in t) >= 2:  # acronym (LS-SLE, AI-writing)
                    continue
                if not _in(w, easy):
                    hard_raw += 1
                    if not _in(w, terms):
                        hard += 1
    if not words or not sents:
        return None
    wps = words / sents

    def dc(h):
        pdw = 100.0 * h / words
        return 0.1579 * pdw + 0.0496 * wps + (3.6365 if pdw > 5 else 0)
    fk = 0.39 * wps + 11.8 * (syll / words) - 15.59
    return round(dc(hard), 1), round(dc(hard_raw), 1), round(fk, 1), words



def lint(path, profile):
    rules = list(SHARED)
    if profile == "published":
        rules += PUBLISHED + word_rules(PUB_WORDS_FAIL, "FAIL", "P6") + word_rules(PUB_WORDS_WARN, "WARN", "P6")
    else:
        rules += INTERNAL + word_rules(INT_WORDS_FAIL, "FAIL", "I5") + word_rules(INT_WORDS_WARN, "WARN", "I5")

    findings = []
    in_code = in_front = off = False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for n, raw in enumerate(lines, 1):
        if n == 1 and raw.strip() == "---":
            in_front = True
            continue
        if in_front:
            if raw.strip() == "---":
                in_front = False
            continue
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not raw.strip():
            continue
        if re.fullmatch(r"\s*(-{3,}|\|[\s\-:|]+\|)\s*", raw):  # hr / table rule
            continue
        if "<!-- sle-off -->" in raw:
            off = True
            continue
        if "<!-- sle-on -->" in raw:
            off = False
            continue
        if off or raw.lstrip().startswith("<!--"):
            continue
        text = re.sub(r"`[^`]*`", "``", raw)  # inline code exempt
        text = re.sub(r"\]\([^)]*\)", "]()", text)  # link targets exempt
        text = re.sub(r"https?://\S+", "URL", text)  # bare URLs exempt
        text = re.sub(r"\[\[[^\]]*\]\]", "[[link]]", text)  # vault filenames use " -- "
        masked = mask_quotes(text)
        if profile == "internal":
            for a in INT_ALLOW:
                masked = re.sub(a, lambda m: "§" * len(m.group(0)), masked, flags=re.I if "PUBLISHED" not in a else 0)

        for rule, sev, pat, msg in rules:
            for m in re.finditer(pat, masked):
                hit = m.group(0).strip()
                if rule == "P7" and hit.split("-")[0] in ACRONYMS:
                    continue
                if rule == "P6" and sev == "WARN" and raw.startswith("# "):
                    continue  # one 'actually' etc. allowed in the headline
                if rule == "P7" and re.fullmatch(r"[A-Z]{4,}", hit) and hit in ACRONYMS:
                    continue
                findings.append((n, sev, rule, msg, snippet(masked, m.start(), m.end())))

        sents = sentences(mask_quotes(text))  # quoted words are not ours; don't count them
        if profile == "published" and not re.match(r"\s*([-*+]|#+|\d+\.)\s", raw):  # not lists or headings
            run = 0
            for s in sents:
                run = run + 1 if len(strip_md(s).split()) < STACCATO_WORDS else 0
                if run == STACCATO_RUN:
                    findings.append((n, "WARN", "P10", "staccato run (3+ short sentences in a row): a common AI-writing rhythm",
                                     s[:70]))
        for s in sents:
            wc = len(strip_md(s).split())
            if wc > SENT_MAX[profile]:
                findings.append((n, "WARN", "P8" if profile == "published" else "I4",
                                 f"sentence is {wc} words (max {SENT_MAX[profile]})",
                                 s[:70] + ("…" if len(s) > 70 else "")))
    if profile == "published" and ENABLE_H6:
        findings += list_direction_check(lines)
    if profile == "published":
        r = readability(lines)
        if r and r[0] > DC_MAX:
            findings.append((0, "WARN", "P12b",
                             f"Dale-Chall {r[0]} (max {DC_MAX}; {r[1]} before the terms-of-art allowlist; FK {r[2]}, not gated)",
                             f"{r[3]} prose words scored. Rewrite at a 10th-grade level (P12a)."))
        for n, h, sc, wc in readability_blocks(lines):
            findings.append((n, "WARN", "P12b", f"block over Dale-Chall {DC_MAX}: {sc} ({wc} prose words)",
                             f"## {h}"))
    return findings


def snippet(s, a, b, pad=30):
    lo, hi = max(0, a - pad), min(len(s), b + pad)
    return ("…" if lo else "") + s[lo:hi] + ("…" if hi < len(s) else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--profile", choices=["published", "internal"], required=True)
    ap.add_argument("--fail-only", action="store_true", help="hide WARN lines")
    args = ap.parse_args()

    total_fail = total_warn = 0
    for path in args.files:
        fs = sorted(lint(path, args.profile))
        fails = sum(1 for f in fs if f[1] == "FAIL")
        warns = len(fs) - fails
        total_fail += fails
        total_warn += warns
        print(f"== {path}  [{args.profile}]  {fails} FAIL, {warns} WARN")
        for n, sev, rule, msg, snip in fs:
            if args.fail_only and sev == "WARN":
                continue
            print(f"  L{n:<4} {sev:<4} {rule:<3} {msg}\n         {snip}")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
