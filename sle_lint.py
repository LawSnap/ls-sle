#!/usr/bin/env python3
"""sle_lint.py: lint for LS-SLE 2026-10-04 (LawSnap Simplified Legal English).

Flags the mechanical rules in the LS-SLE rulebook (README.md in this repo).
Judgment rules (S1, S3, S4, P1, P9, P11, I2, I3, I6, and the structure layer) stay manual.
https://github.com/LawSnap/ls-sle  ·  MIT License (see LICENSE-CODE).

Usage:
    python3 sle_lint.py FILE [FILE ...] --profile published|internal

Exit code 1 if any FAIL. WARN never fails the run.
Text inside double quotes is exempt (quoted sources are not yours to edit).
Text between <!-- sle-off --> and <!-- sle-on --> is skipped (for example, a list of banned words).
"""
import argparse
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
