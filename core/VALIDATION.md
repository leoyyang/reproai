# Line 1 validation against real replication packages

This records how the Line 1 static engine was validated — **not** against synthetic fixtures, but
against the project's **real** IV replication packages and the **fix-loop nodes** that the
execution-based reproducibility pipeline actually got stuck on (recorded as runner/janitor
`lessons.md` entries, each tagged with the paper it happened on and how it was fixed).

The question this answers: **does Line 1 statically catch the things that would otherwise make a
package get STUCK in the execution fix loop?** If yes, an author who runs Line 1 before submitting
removes those blockers up front, so the package runs first-try.

> **Why fix-loop lessons, not `author_issues.json`.** `author_issues.json` records code defects we
> ultimately discovered — many of which (data version drift, restricted data, sign flips) are
> scientific/provenance issues no static tool can predict. The **fix-loop lessons** are the actual
> technical nodes where execution halted and a fix was applied — that is precisely what
> pre-diagnose exists to prevent. The two validations below reflect this: §A is the fix-loop
> validation (the right target); §B is the earlier author-issues cross-check (kept for reference).

## A. Fix-loop node validation (primary)

Each runner/janitor lesson is a place the pipeline got stuck. We classified all 30 candidate
fix-loop lessons (Oracle-assisted) into:
- **class A** — author-preventable AND statically detectable (Line 1's target),
- **class B** — author-preventable but only visible at execution (→ `cannot_predict`),
- **class C** — PIPELINE-INTERNAL (our REGOUT/parser/trace/marker bugs — Line 1 must stay silent,
  not blame the author). 12 of 30 lessons are class C.

Running Line 1 on the original `replication_files/` of each class-A lesson's paper:

| Fix-loop node (lesson) | Paper | Caught by | Result |
|---|---|---|---|
| `clear all` in non-master script | Dietrich2015 | B7 | correct non-fire (paper uses plain `clear`, not `clear all`) |
| `quietly` hides missing `use` | Rueda2017 | B9-suppressed-data-load | HIT |
| reghdfe IV-syntax (version-fragile) | Arias2019 | C4-deprecated-syntax-signature | HIT |
| `.dta` referenced but `.tab` shipped | Gelbach2012 | A8-data-ref-extension-mismatch | HIT |
| renamed data file, missed `use` ref | Gelbach2012 | A8-data-ref-extension-mismatch | HIT |
| user-written ado not shipped (combomarginsplot) | Digiuseppe2022 | C2-vendor-ado | HIT |
| nested/relative `cd` | Xu2024 | A9 / B4 (abs cd) | HIT |
| `table var, c(...)` removed in Stata 17 | Trounstine2016 | C4-deprecated-syntax-signature | HIT |
| commented-out regression citing restricted data | Hariri2024 | A10-commented-restricted-regression | HIT |

**Result: 8/9 caught; the 1 non-hit is a correct non-fire** (the literal `clear all` pattern is not
present in that paper's shipped code; firing on plain `clear` would be a false positive).

### Class-C reframed as normalization advice (not "silent")

Earlier we kept Line 1 silent on class-C (pipeline-internal) fix-loop nodes. That was too narrow:
Line 1 is **prescriptive**, so where a class-C node has a **normalized author writing-style that
sidesteps it**, we now emit that as a low-priority **normalization** advisory (kind=normalization),
worded as "a better way to write it" — never "your code is wrong". Examples:

| Class-C fix-loop node | Normalized advice (new rule) |
|---|---|
| `#delimit ;` broke our marker injection | N1 — use `///` line continuation instead |
| nested-loop unroll produced wrong regressions | N2 / B1 — write one explicit command per model |
| R multi-line comment cleaning left dangling args | N3 — write compact, balanced table calls |
| scalar-wrapper / bare calls bypass our trace | N4 — call estimators directly (named) |

Truly tooling-only class-C nodes with **no author-side writing change** (our e(b) recovery mapper,
jsonl-not-written, trace prolog `$` bug, did2s trace gap, generic loop-control symptoms) remain
out of scope — we do not blame authors for our bugs.

### Priority model (P0–P4 by downstream reproducibility cost)

Findings are now graded by **downstream cost**, not "right/wrong": P0 blocks reproduction; P1 large
fix-loop cost; P2 moderate misread risk; P3 minor; P4 compliance/polish. Each finding is also tagged
`kind` = defect | normalization. The advisory plan is priority-sorted so an author can fix "P0 only",
"P0+P1", or "all". Reference: `style_guide.md` (normalized Stata/R writing forms).

New detectors added: A8 (data-ref extension mismatch), A9 (nested cd), A10 (commented restricted
regression), B9 (suppressed data-load), B10 (embedded foreign code), C2 (vendor-ado, implemented),
C4 (deprecated-syntax signatures), N1 (#delimit), N2 (explicit table commands), N3 (compact R table
calls), N4 (named estimation calls). Rule count: 28 (15 defect / 13 normalization).

False-positive guard: a clean, well-formed package (version-pinned, xtset, relative paths, base
`reg` + `esttab`) produces **0 advisory items** — the new detectors do not over-fire.

## B. Author-issues cross-check (secondary, kept for reference)

The earlier cross-check below ran against `author_issues.json`. It conflates author-preventable
fix-loop blockers with scientific/provenance defects that are out of static scope; §A above is the
authoritative validation.

## Method

- Validation set: the 19 IV papers in `workspaces/iv/*` that have an `author_issues.json`
  (the ground-truth record of issues the fix loop found).
- For each paper, run `line1 check workspaces/iv/<paper>/replication_files --venue aea`
  on the **original author-submitted** `replication_files/` (pre-cleaning).
- Compare Line 1's advisory items against each recorded real issue.
- Classify each real issue as **statically catchable** (a static signal exists) or
  **out of static scope** (needs execution, the paper PDF, or author knowledge).

## Result (2026-06-15)

**Statically-catchable real issues caught: 10/10.**
**Out-of-static-scope issues (correctly not attempted): 21.**

| Paper | Real issue | Catchable by | Result |
|---|---|---|---|
| Charron2013 | guarded dead fallback loads wrong data file | A6-guarded-fallback-load | HIT |
| Charron2017 | no data-load command | A3-data-load | HIT |
| Pupaza2023 | no `use` command | A3-data-load | HIT |
| Vernby2013 | never loads data | A3-data-load | HIT |
| Dube2015 | data shipped under different name | orphan (referenced_missing) | HIT |
| Gerber2010 | references rawdata/ files not included | orphan (referenced_missing) | HIT |
| Tajima2013 | cleaning scripts without raw inputs | orphan (referenced_missing) | HIT |
| Schubiger2021 | only .tab shipped, .dta referenced | orphan (referenced_missing) | HIT |
| Blattman2014 | variable used but never defined (lifecycle) | A7-var-lifecycle-contradiction | HIT |
| Hager2022 | R stargazer/xtable syntax errors | B8-r-table-call-syntax | HIT |

### Out of static scope (documented in each report's `risk_register.cannot_predict`)

Data version drift (Charron2013), original data irretrievable (Charron2013),
omitted table model / absent outcome var (Charron2017), published-PDF divergence (Laitin2016),
only-subset-shipped (Dube2015), missing identifier/classification files (Lorentzen2014),
bare `svy:` in loop halts (Blattman2014), restricted data (Coppock2016, Rueda2017, Hager2022),
standardization/scaling reporting (Kapoor2018), paper-side sign flip (Horz2023),
multiple-imputation pooled estimates (Rueda2017), released-code-wrong-for-columns (Stewart2017),
unguarded `_b[]` after `mi estimate` halts (APSR2018), `keep`-exclusion of a later-used variable
(Croke2016, Stewart2017 — deliberately LEFT OUT: with `.dta` columns invisible and wildcard
keeplists, a generic keep/undefined-variable detector is false-positive-prone and would erode
author trust; only the safe `drop`/`rename`-then-reuse subset is detected, via A7).

## C. Graph substrate + new detectors (0.4.7, 2026-06-27)

The 0.4.7 detectors (A5 now emitting, A14 missing-input, A15 ambiguous-input, C8 unseeded-stochastic,
D7 codebook-coverage) and the `reproai map` command were **motivated** by a real end-to-end build: a
package that passed `reproai check` clean at several points where it did not yet reproduce (a missing
input, a nondeterministic step, output→exhibit mapping). They are currently validated by **fixtures —
a positive AND a negative case per detector** (`tests/test_graph_substrate.py`,
`tests/test_missing_inputs.py`, `tests/test_phase3_detectors.py`, `tests/test_output_map.py`), with
the negative fixtures as the real deliverable (they are what catch the next false positive in CI).
Real-package corpus validation in the style of §A is still owed; until then these are graded as
fixture-validated, not corpus-confirmed. Design note:
`docs/design/2026-06-26-graph-and-detector-roadmap.md`; change list: `CHANGELOG.md` (plugin 0.4.7).

## Honesty note

These numbers are about **static catchability**, not "first-try pass guarantee". Pre-diagnose
maximizes the chance the downstream check passes first-try by removing avoidable failures; it
cannot guarantee it, because numerical match, environment reconstruction, and runtime behavior
only surface at execution. That limit is stated in every `risk_register.json`.

## Reproduce

```bash
pip install -e .
for p in workspaces/iv/*/ ; do
  [ -f "$p/author_issues.json" ] || continue
  line1 check "$p/replication_files" --venue aea --out "$p/.reproai/reports"
done
```
