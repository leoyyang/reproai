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

## venue profile — add `econsoc` (Econometric Society) (2026-06-16)

- Added the `econsoc` venue profile (profile_version 2026-06-15), 8 checks, for Econometrica,
  Quantitative Economics, and Theoretical Economics. Deposit to the Econometric Society Journals'
  Community at Zenodo after the Data Editor's reproducibility checks; SSDE template README strongly
  encouraged; one-month deposit window; five-year preservation for exempted restricted data. Reuses
  the existing detector set (no engine change); added to the venue-profile test matrix.

## rules_version 2026.06.18: reproducible parallel RNG (C7)

- Added `C7-nonreproducible-parallel-rng` (P1, propose_only). An R file using a `foreach(...) %dopar%`
  loop (or a doParallel backend) without doRNG (`%dorng%` / `registerDoRNG`) draws a different RNG
  stream per worker, so bootstrap and simulation results are not reproducible. Target form: doRNG.
  From a JASA referee on the `fdid_paper` package, who flagged exactly this and required a re-run of
  Table 1. Rule count 36 -> 37.

## venue profile: add `jasa` (JASA) (2026-06-18)

- Added the `jasa` venue profile (profile_version 2026-06-18), 10 checks, for the Journal of the
  American Statistical Association (Applications & Case Studies, and Theory & Methods with original
  submission on or after 2021-09-01), per the JASA Reproducibility Guide
  (jasa-acs.github.io/repro-guide): ACC form, JASA template README (with a results-to-be-replicated
  map), master script, declared environment and cores, relative paths, raw-to-analysis preprocessing,
  LICENSE, reproducible RNG (rule C7), and deposit to a Git repo plus reproducibility_materials.zip.
- Small engine refinements so the profile is correct on real JASA packages: case-insensitive README
  detection (the JASA template ships `ReadMe.pdf`, which the case-sensitive detector missed); a
  profile-supplied `readme_sections` override (JASA's template uses "Results to be Replicated", not
  the default hints); a soft `readme_at_root` detector (PDF recommended, not a hard fail); and a
  `license_at_root` detector (a referee flagged a missing LICENSE). Added `jasa` to the venue-profile
  test matrix.

## plugin 0.4.1: JASA venue, reproducible-RNG rule, README workflow (2026-06-18)

- Bumped the plugin to 0.4.1 (Claude marketplace and manifest; Codex manifest brought up from 0.3.0
  to match) for the new `jasa` venue, the C7 reproducible-parallel-RNG rule, and the issue #3 README
  improvements below.

## README workflow: read PDF READMEs + flag duplicate READMEs (issue #3, 2026-06-18)

Partial resolution of issue #3 (streamline the README workflow), items (1) and (3):

- The venue README-sections check now READS PDF READMEs. When a package ships no markdown/text README,
  the engine extracts the PDF text via poppler's `pdftotext` (graceful fallback when poppler is absent)
  and checks it against the section checklist, instead of returning a non-actionable "section content
  not statically inspectable". Verified on the JASA `fdid_paper` package with its markdown README
  removed: the PDF's sections are now credited.
- Added `D5-duplicate-readme` (P2, propose_only). Flags multiple distinct README documents (different
  names or folders) that can diverge and mislead a replicator; a same-name `README.md` + `README.pdf`
  pair counts as one document and is not flagged. From issue #3, where an APSR package shipped two
  divergent README drafts. Rule count 37 -> 38.
- Issue #3 items (2), (4), (5) are addressed in the next entry.

## README workflow: scaffold generator, missing-path check, PDF render (issue #3, 2026-06-18)

Remainder of issue #3 (items 2, 4, 5):

- (2) `reproai readme --scaffold` emits a README.md DRAFT assembled from the package's own structure:
  a file manifest with inferred roles, the run order (entry/master scripts), a results map
  (table/figure -> source:line -> output), and the detected language and packages. Author-only fields
  are marked `[CONFIRM]`; nothing is invented. The engine emits the draft deterministically instead of
  delegating README authoring to free text. Verified on the `fdid_paper` package.
- (4) Added `D6-readme-missing-paths` (P3, propose_only). Flags a backtick-quoted README path (a folder
  ending in `/` or a file with a code/data extension) that does not resolve to anything in the package.
  Only backtick-quoted tokens are checked, so folder-tree diagrams and prose never false-fire (verified
  clean on the `fdid_paper` README, whose tree names an illustrative `replication/` root). Rule count
  38 -> 39.
- (5) `reproai readme --render` renders `README.md` to PDF via pandoc (and prints the one-liner if
  pandoc is absent), so keeping the markdown and PDF READMEs in sync is one command.

## packaging checks from a best-practice review (2026-06-18)

Additions distilled from reviewing external replication-package best-practice guidance (the source is
credited in the GitHub README's "Recommended reading" section):

- Added `A13-unreferenced-script` (P2, propose_only). When a package has a master/sourcing structure,
  flags a code file that nothing runs and whose name appears in no other script (a likely exploratory
  or obsolete leftover). A helper sourced via a path the scan could not resolve is not flagged, since
  its name still appears in the caller. Stays silent on the `fdid_paper` package.
- Added `N5-unsafe-filename` (P3, propose_only). Flags a script or data filename with a space or a
  shell-unsafe character that breaks command-line runs and master scripts.
- README scaffold upgrades: the results section is now a crosswalk table (output / produced-by /
  saved-to), plus a data-sources-and-availability block that prompts for restricted-data details and a
  "Last verified" line. Rule count 39 -> 41.

## plugin 0.4.2: /reproai:contribute (community contributions) (2026-06-19)

A new `/reproai:contribute` command lets users send lessons back as structured GitHub issues. reproai
never posts: it builds a pre-filled new-issue URL the user submits, and never includes package data.

- Three modes: a missed rule, a false flag (both feed the rule-lesson flow), and a NEW VENUE (a journal
  not yet supported, with its replication policy).
- New-venue mode: a citation gate (official policy URL required, or refuse), a verbatim `policy_quote`
  per requirement (so a maintainer verifies fidelity by string-search), detector choices constrained to
  the known set, and dedup against the shipped venues. The deterministic engine does only the mechanical,
  verifiable part; interpreting the policy into detectors stays with the LLM, and fidelity stays human.
  No draft-YAML assembler was built (an independent audit found it would guard nothing CI does while
  manufacturing a confident-wrong-detector failure mode).
- Engine support (`core/src/line1_core/contribute.py` + `reproai contribute`): `--scrub` flags
  identifying content (absolute/home paths, emails, ORCIDs); `--venue <draft.yaml>` blocks on a leak,
  then validates a drafted profile (schema, known detectors, a clean dry-run on a synthetic fixture) and
  green-lights it before it becomes an issue.
- `unbuilt_detector`: a profile may park a statically-checkable requirement with no detector yet as
  `detector: unbuilt_detector` + `needs_detector:`; it emits a distinct `not_applicable` (never a disguised
  manual stub), and `test_no_unbuilt_detectors_in_shipped_profiles` keeps an owed detector from shipping
  forgotten. `venue_engine.run_profile()` lets a draft be dry-run without installing; `KNOWN_DETECTORS`
  is the closed set the validator enforces. The venue test matrix now globs `venues/*.yaml`, so a new
  profile is matrix-tested automatically.
- Issue templates: `venue-contribution.yml` (form) + `.md` fallback, and `lesson-contribution.md`.
- `tools/bump_version.py` now bumps all five version files (it had missed the Codex manifest), guarded by
  a new `test_version_lockstep`; every version file is reconciled to 0.4.2.

## venue profile: add `worldbank` (World Bank Reproducible Research Repository) (2026-06-19)

- Added the `worldbank` venue profile (profile_version 2025-10-20), 8 checks, for the World Bank
  Reproducible Research Repository — the internal reproducibility verification World Bank staff and
  consultants go through (on request, via the intake form) before journal submission. Per the World
  Bank reproducibility-package checklist: a main script that runs all code after changing only the
  top-level directory, a README at root with the order of execution when there is no main script, a
  README stating the software and version used, an outputs-to-scripts mapping, the line(s) in the main
  script to change for a different machine, raw-to-analysis code starting from original data, a Data
  Availability Statement, and the verification request itself. Each check carries a verbatim
  `policy_quote`. Reuses the existing detector set (no engine change); a profile-supplied
  `readme_sections` override matches the checklist's README contents. Added to the venue-profile test
  matrix (auto-discovered via glob). Suggested by Mateo Servent (World Bank).

## plugin 0.4.3: World Bank venue (2026-06-19)

- Bumped the plugin to 0.4.3 (Claude marketplace and manifests, Codex manifest, core package) for the
  new `worldbank` venue profile suggested by Mateo Servent (World Bank). Registered `worldbank` in the
  shipped-venue lists across the check / comply / contribute command docs and Codex skills.

## plugin 0.4.4: World Bank coverage completion (2026-06-19)

Completes the `worldbank` venue profile with the gaps Mateo Servent's audit surfaced (a follow-on to
the 0.4.3 World Bank venue).

- New checks `WB-DATA-RIGHTS` (rights statement), `WB-MANUSCRIPT` (final manuscript), `WB-RAW-OUTPUTS`
  (raw tables/figures), and `WB-CODE-BUILDS-EXHIBITS` (code creates all exhibits and in-text numbers),
  each with a verbatim `policy_quote`; extended `WB-DATA-AVAILABILITY` to mention the rights statement
  and per-dataset source/URL/access-year; added the "guides future readers" / "guidance for the
  reviewer" hints to the `WB-README-SECTIONS` requirement text.

## plugin 0.4.5: unified manual-action / honesty taxonomy + 3 new static detectors (2026-06-19)

Engine feature: every venue check now reports an honest status, and "checkable-in-principle" items
that were stubbed are now real detectors.

- Three-tier status taxonomy. `manual_author_action` keeps `needs_author_action` but its `detail` is
  now the check's own `author_action`-or-`requirement` (not the generic "cannot be verified
  statically" stub). `unbuilt_detector` now emits the NEW status `not_implemented` (was the
  misleading `not_applicable`), keeping `needs_detector`. `not_applicable` is reserved for genuinely
  inapplicable conditional requirements. The venue summary gains a `not_implemented` count.
- `Check` carries optional, author-facing guidance fields `author_action` / `how` / `self_check`
  (and `needs_detector`); `reports.py` emits them only when populated. They are grounded in the
  requirement + source, are NOT policy quotes, and NEVER change a status (anti-sycophancy boundary).
- 3 NEW static, no-execution, low-false-positive detectors added to `KNOWN_DETECTORS`:
  `data_availability_statement` (root README scan for a Data Availability Statement: pass / fail when
  no README / needs_author_action when present without one), `data_citation` (README + code/text scan
  for a DOI / handle / Dataverse-Zenodo-ICPSR-OSF URL), and `seeded_rng` (R code-shape scan: a
  parallel loop with no reproducible-RNG signal → needs_author_action; never executes code).
- Reclassified the 4 mis-tiered checks onto the real detectors: `WB-DATA-AVAILABILITY` and
  `APSR-DATA-AVAILABILITY` → `data_availability_statement`; `GEN-DV-DATA-CITATION` → `data_citation`;
  `JASA-REPRO-RNG` → `seeded_rng`.
- Added `author_action` / `how` / `self_check` guidance to the remaining `manual_author_action` checks
  across aea, ajps, jop, econsoc, apsr, jasa, worldbank.
- Schema: `not_implemented` added to the status enum; optional `author_action` / `how` / `self_check`
  / `needs_detector` fields and a `not_implemented` summary count.
- Command docs: `check.md` (and the Codex check skill) present `needs_author_action` items as a
  separate "Pre-submission author actions" checklist and `not_implemented` items as "reproai can't
  check this yet"; `fix.md` / `debug.md` record an author's self-attestation as a NOTE only — the
  engine status never changes. New `venues/README.md` documents the taxonomy for maintainers.
- Tests: schema test covers the new statuses/fields; added a test that a manual_author_action check's
  detail equals its author_action-or-requirement, and a test that the 4 reclassified checks compute a
  real status. 67 passing.
- Version bumped to 0.4.5 across all six version files (the Claude + Codex manifests, both
  marketplace.json files, pyproject.toml, __init__.py). The World Bank coverage completion (0.4.4
  above) shipped in the same build; the changelog lists it separately to keep the version sequence
  continuous.

<!-- Append new entries above this line. Each entry: bump rules_version, list added/changed rule ids
     and the Line 2 lesson(s) they were promoted from. -->
