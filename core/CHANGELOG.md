# Changelog — line1 knowledge base

Tracks the **content** versions of the author rule set, venue profiles, and style guide —
separate from the engine code version in `pyproject.toml`. The plugin reports these so an author
knows which knowledge revision diagnosed their package; the downstream Line 2 pipeline feeds new
rules in over time (improve-with-use).

Versioning: `rules_version` is date-based `YYYY.MM.DD` (bump when a rule is added/changed/promoted).

## rules_version 2026.06.15

- Initial author rule set: 28 rules (15 defect, 13 normalization), graded P0–P4 by downstream
  reproducibility cost.
- AEA venue profile (profile_version 2026-06-15), 9 checks.
- Normalized coding style guide (Stata + R).
- All rules carry `source_lessons` traceable to Line 2 runner/janitor/matcher lessons.
- Validation: 8/9 statically-catchable fix-loop nodes caught on real replication packages;
  class-C pipeline-internal nodes reframed as low-priority normalization advice where a normalized
  author writing-style sidesteps them.

## plugin 0.3.0 (2026.06.16)

- Added 5 venue profiles: `apsr`, `ajps`, `jop` (Harvard Dataverse, CC0; AJPS = Odum pre-acceptance
  verification, APSR/JOP in-house), plus `generic_dataverse` and `generic_openicpsr` fallbacks.
- Added `line1 fix` + `/reproai fix`: applies ONLY auto-safe (semantics-preserving) transforms to a
  COPY, dry-run by default, original never touched. v1 auto-safe set = B9 (drop `quietly` on a
  data-load) and B11 (comment an R Markdown fence in a `.R` file); everything else is propose-only.
- Fixed venue engine `file_count_limit` crash when a profile sets `max_files: null`.

## rules_version 2026.06.16

First batch promotion from the distiller (reviewed from 241 candidates; 4 added, 1 extended).
All author-preventable, statically detectable, low-false-positive, corpus-confirmed:

- Extended `C4-deprecated-syntax-signature` — now also flags legacy Stata mixed-model commands
  (`xtmelogit`/`meqrlogit`/`xtmixed`, which hang/are removed on modern Stata) and `cd ""`
  (switches to HOME, breaks relative paths). From AJPS2014, janitor lessons.
- Added `C5-deprecated-r-packages` (P1) — `library(rgdal/rgeos/maptools/ZeligMultilevel/checkpoint/
  hrbrthemes/arm)` halts the script. Corpus-confirmed (rgdal/rgeos in multiple papers).
- Added `C6-old-stata-merge-syntax` (P1) — pre-Stata-11 `merge varlist using` fails on modern Stata.
  Corpus-confirmed (Ritter2016).
- Added `B11-rmd-chunk-in-r` (P0) — R Markdown ```{r} markers in a `.R` file cause a parse error.

Deferred (kept in seedbank, not promoted): pipeline-internal lessons (our REGOUT/parser/trace
internals), and lessons needing execution or the paper (declared-model-count, NA-laden covariate
drift). Rule count: 28 -> 31 (3 added: C5, C6, B11; C4 extended in place).

## plugin 0.3.0 — LLM-driven lossless rewrite loop + naming cleanup (2026-06-16)

Reframes `/reproai-fix` from a 2-transform hardcoded fixer into an LLM-driven, report-guided,
lossless rewrite loop (DECISIONS D8). No reproducibility verdict, no code execution.

- **Advisory schema v2 → v3.** Every rule now carries `why_downstream`, `target_form`,
  `lossless_note`, and `propose_only`. `advisory_plan.json` items gain a `rewrite` block
  (`mode` = `llm_rewrite` | `propose_only`, `lossless_note`, and a self-contained `fix_prompt`),
  and the report carries a universal `lossless_contract`. Rule classification: 20 `llm_rewrite`,
  11 `propose_only` (data re-derivation, dead-fallback load, sample/merge cardinality,
  estimator/formula, panel keys, restricted-data scope, wide wildcards).
- **`/reproai-fix` rewritten** to: read the advisory → copy to `<root>_fixed` → host LLM applies
  each `llm_rewrite` finding under the lossless contract → re-run `reproai check` → iterate
  (cap 3 rounds) until findings clear → hand the author the diff + propose-only recommendations.
  The pre-existing 2 mechanical transforms (B9/B11) remain as an optional Tier-0 `--apply` shortcut.
- **Anti-sycophancy preserved.** The engine still owns every finding/priority/eligibility decision;
  the new test `test_no_reproducibility_verdict` continues to forbid verdict tokens in output
  (caught and fixed 4 prose leaks during this change).
- **Naming cleanup (DECISIONS D7).** User-facing `line1` → `reproai`: CLI console script
  (`reproai check`), all command files, agents, and the plugin folder (`plugins/line1` →
  `plugins/reproai`). Internal Python package `line1_core` unchanged (import path only).
- **`build_public.py`** carries the 4 new fields into the public bundle (no paper-name leak; the
  publish anonymity gate still strips `source_lessons`).
- **Tests:** +2 (`test_every_finding_carries_a_rewrite_contract`,
  `test_propose_only_rules_never_marked_rewritable`); 21 pass. Internal e2e harness added at
  `tests/` (gitignored, untracked) — validated the loop on the real Chong2019 package
  (4 findings → 0 in 3 rounds; original byte-for-byte unchanged).

## rules_version 2026.06.19 — table<->command mapping comments (A12)

- **A12-table-comment-mapping (P2, normalization).** Fires when a script has multiple estimation
  commands but NO `* Table N` / `* Figure N` comments anchoring the table<->command mapping. Closes
  the gap where D1 (per-table export) and Line 2's matcher depend on author comments that may not
  exist. Fix DRAFTS the grouping and inserts PLACEHOLDER anchors
  (`* --> Table ?? (reproai: author, confirm number)`) — the LLM proposes the grouping from code
  structure but never invents the table number (a paper fact not in the code). Rule count 35 → 36.
  Dependency order is now **A12 (anchor) → N2 (unroll) → D1 (export)**, documented in fix.md.

## rules_version 2026.06.18 — per-table D1 + per-file documentation (D4)

- **D1-output-artifact-coverage now reports PER TABLE/FIGURE SECTION.** It anchors on `* Table N` /
  `* Figure N` comment headers and flags each section that builds estimates/graphs without an export,
  instead of one whole-file finding. On Chong2019 it now surfaces all 15 table sections
  (Table 1-4 + Table A.1-A.11) individually, so fix injects an export for every table, not just one.
- **D4-per-file-documentation (P3, llm_rewrite).** Flags scripts/data files not described in any
  README (per-file purpose, inputs/outputs, codebook location). Fix DRAFTS README documentation —
  purely additive (writes new markdown, never edits/runs code). Rule count 34 → 35.

## rules_version 2026.06.17 — intermediate-output + run-order + intermediate-data rules

Three new rules for what a good replication package needs beyond the final estimates
(DECISIONS D8 carry-over; user request 2026-06-17). Rule count 31 → 34.

- **D1-output-artifact-coverage (P2, llm_rewrite)** — each reported table's estimates and each figure
  should be saved to a relative output folder (`output/tables`, `output/figures`). Detects estimation
  with no table-export and graphs with no graph-export. Fix INSERTS additive export commands (cannot
  change a coefficient). Reported as "artifact-output coverage incomplete", never as a named-table
  claim (the linter does not read the paper PDF).
- **A11-explicit-run-order (P1, propose_only)** — a multi-script package must document its execution
  order (master script OR README ordered list); flagged when neither exists.
- **D3-intermediate-data-hygiene (P1, propose_only)** — a dataset written by one script and read by
  another should live under a canonical `data/` folder, have an existence guard before the dependent
  read, and ship with the package. Detects cross-script intermediate-data writes outside `data/`.

## plugin 0.3.0 — execution capability + /reproai-debug; static iron rule abolished (2026-06-17)

The founding "Line 1 never executes code" rule is **abolished** (DECISIONS D10) to let authors
smoke-test a package after fixes. The numerical boundary is preserved: reproai still never compares
coefficients and never issues a reproducibility verdict.

- **New `/reproai-debug` slash command (DECISIONS D11).** The one command that RUNS the package — a
  smoke test on a COPY: does it run end-to-end, and did the injected D1 table/figure outputs appear.
  On a runtime error it does NOT auto-fix: it explains the root cause, offers 2–4 options, and calls
  the host `AskUserQuestion` tool to let the author decide, then applies the chosen fix and re-runs.
  Built as a slash command (not a subagent) because `AskUserQuestion` is unavailable to subagents.
- **Boundary language updated.** Plugin-level description now states the static commands
  (check/comply/fix) do not execute code while the optional debug command runs a smoke test; the
  per-static-command "never execute" claims are kept (still true for those surfaces). reproai still
  "never compares coefficients / never issues a reproducibility verdict" everywhere.
- **Tests:** +2 (`test_d1_fires_when_estimation_has_no_export`,
  `test_a11_and_d3_fire_on_multiscript_intermediate`); 23 pass. Clean-package noise test extended to
  forbid false D1/D3 fires. New internal multiscript fixture under `tests/fixtures/` (gitignored).

<!-- Append new entries above this line. Each entry: bump rules_version, list added/changed rule ids
     and the Line 2 lesson(s) they were promoted from. -->
