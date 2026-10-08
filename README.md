# LS-SLE 2026-10-08: LawSnap Simplified Legal English

A finite, checkable writing standard for legal content written by people and AI models together. It comes with a lint script that flags the mechanical rules.

**Version:** 2026-10-08. The version is the ISO date of the release. A newer date means a newer version.

## Why this exists

We publish data-driven findings about how courts rule. Two problems kept showing up:

1. **AI-writing tells.** Drafts came back full of em dashes, "it isn't X, it's Y" reversals, and hype labels like "the trap nobody warns you about." Readers notice, and their trust drops.
2. **Term confusion.** Several AI agents work on the same pipeline. When one wrote "ready" and another read "approved for publication," work shipped that shouldn't have.

Aerospace solved a version of this decades ago with ASD-STE100 (Simplified Technical English): short sentences, one meaning per word, and a short rulebook you can check. LS-SLE applies that idea to legal writing. It adds a second layer, from Robert Horn's Information Mapping, for how blocks of text are laid out.

LS-SLE is an independent adaptation. It is not affiliated with or endorsed by ASD, which owns the ASD-STE100 standard.

## How to use it

```
python3 sle_lint.py FILE.md --profile published
python3 sle_lint.py FILE.md --profile internal
```

- **FAIL**: fix it before the piece goes to cite-check or review. Any FAIL gives exit code 1, so you can put the lint in a pipeline.
- **WARN**: a person decides. Some flagged words carry meaning in context, and those stay.
- Text inside double quotes is exempt. Quoted sources are not yours to edit.
- Text between `<!-- sle-off -->` and `<!-- sle-on -->` is skipped (useful for a list of banned words).
- Rules marked [manual] have no lint check. The writer checks them.
- Requires Python 3. No dependencies, except P12b (Dale-Chall), which runs only if `textstat` is installed: `pip install textstat`.

Zero FAILs does not mean the draft is good. A draft can pass the lint and still read flat. See [Voice keeps](#voice-keeps).

## Two profiles

| Profile | Applies to | Goal |
|---|---|---|
| INTERNAL | work orders, SOPs, agent instructions, tickets | No ambiguity between the people and agents doing the work. |
| PUBLISHED | articles, emails, social posts | Reader trust. The author's voice stays. |

Personal essays and other writing that is meant to sound like one author are out of scope. A house style is the wrong tool for that.

---

## Shared rules (both profiles)

**S1. One word, one meaning.** Pick the counting unit once. Use it every time. [manual]
If a piece says "127 requests" in one place and "127 motions" in another, those are different units. In our own testing, this rule found real counting errors that a citation check had missed.

**S2. No dashes as punctuation.** Use a period, comma, colon, or parentheses. [FAIL]
This covers the em dash, a spaced en dash, and a double hyphen. Number ranges ("1–9999") are allowed.

**S3. Every number has a denominator or a date.** Write "4 of 14" or "as of 2026-09-28." Do not write "most" or "many" when you have the count. [manual]

**S4. Active voice when the actor matters.** Write "The court struck the pleadings," not "Pleadings were stricken." A short passive is fine when the actor is obvious. [manual]

---

## PUBLISHED rules

**P1. In the first two sentences, give the situation the reader is in, then the number.** No background opener. [manual]
Example: "When a party moves for non-discovery sanctions in California, the court rarely awards them: about 7% of the time for a frivolous filing."

**P2. No contrast-reversal.** State the fact. Do not deny a claim nobody made. [FAIL]
- "isn't X, it's Y" → state Y.
- "didn't just X, it Y" → state X and Y.
- "X isn't the question. Y is." → state Y.

Allowed: a real contrast between two findings ("7% here, against 57% for discovery sanctions").

**P3. No sentence that starts with "Not."** The "Not X. Y." fragment pair is a tell. [FAIL]
"not just" in mid-sentence is a WARN.
Allowed: a short fragment that states a fact ("She wasn't.").

**P4. No hype labels.** Cut them. The fact carries the weight. [FAIL]

**P5. No negation stacks.** "not sampled, not coded from a summary field" → say what you did. [WARN]

**P6. Banned words.** Use the replacement from the list below. [FAIL or WARN, per the list]

**P7. One emphasis per section.** Bold, italic, or CAPS. Pick one. Do not stack them (`***not***`). An author's deliberate CAPS can stay. [WARN]

**P8. Sentences: 45 words maximum.** Quoted words do not count. [WARN]
45 words is the mechanical backstop. P12a is where sentences get shorter.

**P9. Say each number once, in its strongest place.** [manual]

**P10. No staccato runs.** Three or more sentences in a row under 6 words, outside a list, is a common AI rhythm. One short sentence for impact is fine. [WARN]

**P11. Register follows the channel.** A findings page uses a sober register. Social can run hotter. Register varies by subject. [manual]

**P12a. Rewrite at a 10th-grade reading level.** [manual] Do it right after the first draft, in every format. Rewrite for plainness: short sentences, common words, one idea per sentence. Keep these exact: quoted court language, case names, citations, and every number with its denominator. Keep legal terms of art. Simplify the sentence around the term, not the term itself.

**P12b. Vocabulary backstop.** [WARN above Dale-Chall 7.9] The lint scores Dale-Chall, not Flesch-Kincaid. Dale-Chall tracks unfamiliar words, which is what makes legal writing feel clunky; Flesch-Kincaid tracks sentence and syllable length. Flesch-Kincaid is reported next to the score but does not gate.
- **Prose only.** Headings, table cells, quotes, case names, citations, case numbers, section cites and links are not scored.
- **Terms-of-art allowlist** (`terms-of-art.txt`). Legal vocabulary (demurrer, punitive, habitability) does not count against you, so the score measures your word choice, not the law's. Add only legal or litigation words. Your own analytic words ("corpus," "dispositive," "aggregate") stay off. Ordinary words the old Dale-Chall list flags ("specific," "pattern," "whether") stay counted on purpose.
- **Per block.** The WARN names each `##` section scoring over 7.9 (sections with at least 80 prose words), plus the whole piece.
- **Why 7.9.** On Dale-Chall's own scale, 7.0 to 7.9 is grades 9 to 10. In our calibration on 21 legal findings articles, whole-file scores ran 9.6 to 11.8, and prose-only scores after the allowlist ran 6.2 to 8.1.

**P13. The headline states the reader's situation.** [manual] The title answers "what does this mean for me," not "what did we do." Lead with the reader's question or situation. Put the sample size and "we read N rulings" in the sub-line or the lede, never in the headline. This also applies to email subject lines and social openers.
- Bad: "Emotional Distress Claims Against Landlords: What Survives a Demurrer? We Read 352 Claims."
- Good: "When Can You Sue Your Landlord for Emotional Distress?"
- Use a plain, accurate term ("emotional distress"). Never invent one.
- Lint: WARN when the title says "we read/reviewed/coded/analyzed" or carries a sample count ("352 claims").

Legal terms of art are allowed and preferred: grant, deny, tentative ruling, demurrer, safe harbor, meet and confer, with prejudice. Do not "simplify" them.

### Voice keeps

[manual] Keep these. They are voice, not tells:
- Concrete examples with real names.
- A short fragment for impact, used sparingly.
- A closing line that reframes the whole piece.
- Rhetorical questions.
- A colloquial register ("played games in discovery").
- The author's deliberate CAPS.

---

## INTERNAL rules

**I1. One instruction per sentence.** [WARN on "and then," "and also"]

**I2. Put the condition first.** Write "If X, do Y." or "Before X, do Y." [manual]

**I3. Use the imperative.** "Run the lint." Not "The lint should be run." [manual]

**I4. Instruction sentences: 20 words maximum.** [WARN]

**I5. Use only glossary terms for states and roles.** See the banned internal words below. [FAIL or WARN, per the list]

**I6. Name the specific person or agent, not the role.** "The research agent confirmed X" is not traceable when three agents do research. Give the name. [manual]

**I7. Absolute dates only.** Write 2026-10-01. Do not write "today" or "next week." [WARN]

### Build your own glossary

The INTERNAL profile needs a fixed glossary: one term per state, one meaning per term. Ours is specific to our pipeline, so it is not published here. Start with the states your work passes through (drafted, cite-checked, approved for publication, live) and the words people confuse. The rule: if two people can read a term two ways, it goes in the glossary or on the banned list.

One term we found worth defining everywhere: **lead magnet** means the free thing an article offers in exchange for an email address. Its format varies. Say "lead magnet" in general. Say "checklist" only for a lead magnet that is a checklist. In text readers see, use the format name.

---

## Structure layer: Information Mapping

STE governs sentences. Information Mapping governs blocks. A block is a heading, or a bold lead, plus the text under it.

**H1. Chunking.** One block does one job. If a block holds two cases or two kinds of information, split it. [manual]

**H2. Labeling.** Every block has a label that says what is in it. In PUBLISHED, the label states the content ("The other side going silent (4 of 14)"). It does not tease. [manual]

**H3. Relevance.** Put only content of the block's type in the block. Move other content to the block where it belongs. Exception: a voice aside the author keeps. [manual]

**H4. Consistency.** Blocks of the same kind use the same label pattern and the same order in every piece. [manual]

**H6. Group by the issue, not by the outcome.** In "What decides it", each block is one issue the court decided. Show the losing version and the winning version side by side, each with its count. If one side has no count, say so; do not invent one. An item with no pair stays as its own block. [WARN on a list that mixes outcome directions]

Example, motions to strike punitive damages:

| The issue the court decided | What got struck | What survived |
|---|---|---|
| How was malice pleaded? | Where the court cited conclusory labels: struck in 222 of 223 | Where the court cited specific facts about what the defendant knew and did: survived in 298 of 321 |
| Can the claim carry punitive damages at all? | Where only negligence or contract claims remained: struck in 51 of 51 | Where the claim was an intentional tort, usually fraud: survived in 28 of 29 |

- **Format.** The issue-pair table is the main form. Keep the quotes and case examples, inside the cells or in an "Examples" line under each row. Never strip them. Paired bold leads are an acceptable alternative when a piece reads better that way.
- **Label each count by what the court cited.** Each count covers rulings that cited that reason, so it is not a win rate. Say so once in the method note: "These counts describe the court's stated reason, not a predicted chance of winning."
- **Check:** a list's heading must be true of every item in it. If it is not, regroup by issue, split the list, or retitle it so the heading covers every item and state each item's outcome.

**H5. Information types.** Each block holds one type.

| Type | What it answers | Example |
|---|---|---|
| fact | What is true? | "Courts grant about 7% of these requests." |
| concept | What is it? | What a "frivolous filing" means under the statute. |
| principle | What rule or pattern governs it? | "Every grant turned on proof the court could point to." |
| process | How does it work, over time? | A 21-day safe-harbor sequence. |
| procedure | What do I do, step by step? | A work order. A checklist. |
| structure | What are the parts? | The six reasons courts granted the motion. |

### PUBLISHED: block order for a data-driven finding

The block names are internal labels. Published headings can use the author's words. The order and the job of each block stay fixed.

| # | Block | Type | Required |
|---|---|---|---|
| 1 | The number | fact | Yes. May include one sentence on how you looked. |
| 2 | What decides it | structure + fact: one block per issue, losing and winning versions side by side (H6) | Yes |
| 3 | The exception | fact (the subgroup where the overall rate misleads) | When the data shows one, give it its own block right after block 2, headed exactly "Where the average misleads" (any subtitle after a colon). If the data shows none, leave it out. |
| 4 | What to do | principle (the closing line) | Yes. Step-by-step procedures go in a separate checklist, not the article. |
| 5 | Method & N | fact | Yes |

Why block 3 matters: an overall rate can be true and still mislead. State it plainly: "Overall, 29 of 99. Where the complaint alleged a warning, 14 of 19." That subgroup is usually the most valuable thing in the piece.

### INTERNAL: work orders are procedures

Write every work order in this block order:

1. **Do not touch.** The limits come first.
2. **Goal.** One sentence.
3. **Inputs.** Every file, record, and copy. Copies drift; list them all.
4. **Steps.** Numbered. One action per step. Imperative.
5. **Done when.** The end state, by its glossary name.
6. **Report to.** The specific person or agent.

---

## Banned words: PUBLISHED

<!-- sle-off -->
| Banned | Use instead | Lint |
|---|---|---|
| leverage, utilize | use | FAIL |
| delve, dive into | look at | FAIL |
| robust, seamless, empower | cut | FAIL |
| landscape | name the area | FAIL |
| unlock | give, allow | FAIL |
| moreover, furthermore, additionally | also | FAIL |
| it's worth noting, importantly, needless to say | cut | FAIL |
| in sharp contrast, in stark contrast | state both numbers side by side | FAIL |
| testament to, myriad, at the end of the day | cut | FAIL |
| actually | cut (one is allowed in a headline) | WARN |
| really, truly, genuinely | cut, unless it changes the meaning | WARN |
| simply, plainly, clearly, obviously | cut | WARN |
| crucial, critical | cut, or say why | WARN |
| navigate (figurative) | handle | WARN |

## Banned words: INTERNAL

| Banned | Use instead | Lint |
|---|---|---|
| ready | the exact state, from your glossary | FAIL |
| should | must (required) or can (optional) | FAIL |
| etc. | list every item | FAIL |
| and/or | or, and, or "X, Y, or both" | FAIL |
| ASAP, soon, later | a date | FAIL |
| approved (alone) | what was approved, by whom | WARN |
| done (as a state) | the end state, by name | WARN |
| today, tomorrow, this week | a date | WARN |

## Banned patterns: PUBLISHED (the AI tells)

| Pattern | Example | Fix | Lint |
|---|---|---|---|
| Dash as punctuation | "We read every ruling — not a sample." | "We read every ruling." | FAIL |
| isn't X, it's Y | "The deciding factor isn't the argument — it's the evidence." | "The deciding factor is the evidence." | FAIL |
| didn't just X, it Y | "The court didn't just deny the motion — it awarded fees." | "The court denied the motion and awarded fees." | FAIL |
| X isn't the question. Y is. | "Whether they're wrong isn't the question. Whether you can prove it is." | "Ask one question: can you prove it?" | FAIL |
| Not X. Y. | "Not a close call. A clear loss." | "It was a clear loss." | FAIL |
| Hype label | "The trap nobody warns you about." | cut | FAIL |
| River-depth metaphor | "The average river is 3 feet deep, but there's a spot where it's 20." | "Overall, X of Y. In [subgroup], Z of W." | FAIL |
| also: "here's the thing," "the real question," "plot twist," "game-changer" | | cut | FAIL |
| not just | "facts, not just labels" | "facts" | WARN |
| Negation stack | "not sampled, not summarized" | say what you did | WARN |
| Stacked emphasis | `***not***` | one emphasis | WARN |
| Staccato run | "It failed. Again. Badly." | join them, or keep one | WARN |
<!-- sle-on -->

---

## In practice

The first article written under this standard: ["What Actually Gets You Sanctioned in California"](https://lawsnap.com/articles/what-actually-gets-you-sanctioned-in-california/). The original draft had 20 FAILs, including 14 em dashes. The published version has none, and no fact, number, or quote changed.

## Change log

- **2026-10-08:** P12a (10th-grade rewrite), P12b (Dale-Chall vocabulary backstop with a terms-of-art allowlist) and P13 (the headline states the reader's situation). Lint: P12b WARN, optional `textstat`.
- **2026-10-07:** new rule H6, group by the issue, not by the outcome (losing and winning versions side by side, counts labeled by the cited reason). Fixed heading for the exception block. New ban on the river metaphor: state the counts instead. Lint: H6 WARN, river FAIL, exception-heading WARN.
- **2026-10-04:** first public release. It builds on three internal drafts (2026-10-01 to 2026-10-03), each tested on real articles before they went live.

## License

- The rulebook (this README) is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). Credit: "LS-SLE, LawSnap." See [LICENSE](LICENSE).
- The lint script (`sle_lint.py`) is licensed under the MIT License. See [LICENSE-CODE](LICENSE-CODE).

LS-SLE is an independent adaptation. It is not affiliated with or endorsed by ASD, which owns the ASD-STE100 standard.
