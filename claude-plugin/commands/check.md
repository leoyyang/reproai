---
name: reproai-check
description: One-shot static pre-diagnose of a replication package. Scans the working directory, applies the author rule set and a venue profile, and writes 4 JSON reports. Never runs author code. Use when an author wants to know if their replication package is ready to submit, or what to fix before a reproducibility check.
---

# /reproai check — pre-diagnose a replication package

Run the **deterministic** Line 1 engine on the author's package. You (the LLM) orchestrate;
the engine makes every pass/fail and risk-tier decision. You never decide reproducibility and
never execute the author's code.

## Steps

1. Determine the package root (default: current directory) and the target venue (ask the author
   if unknown). Shipped venue profiles: `aea`, `econsoc`, `apsr`, `ajps`, `jop`, plus `generic_dataverse` and `generic_openicpsr` fallbacks.

2. Run the core engine:

   ```bash
   reproai check <ROOT> --venue <VENUE> --out <ROOT>/.reproai/reports
   ```

   If `reproai` is not on PATH, run from the bundled core:

   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/core/src" python3 -m line1_core.cli check <ROOT> --venue <VENUE> --out <ROOT>/.reproai/reports
   ```

3. Read the 4 reports the engine wrote:
   - `architecture_report.json` — entry points, dependency graph, **table→command map**, orphans
   - `advisory_plan.json` — remediation items (each `low`=auto-applicable / `high`=propose-only)
   - `venue_compliance_report.json` — per-requirement pass/fail vs the venue
   - `risk_register.json` — what would likely break a downstream reproducibility run
   Also read the result's **`adversarial_review` block** (the engine's deterministic cross-check):
   surface any `conflicts` (where the rule line and the venue/compliance line point in opposite
   directions) and any risk-tier over-reach it flags. Present them as-is; do not pick a side or
   override them — the engine computed them, you only make them impossible to miss.

3b. **Environment reproducibility note.** From the dependency findings (`C1` unpinned deps, `C2`
   unvendored user commands, `C3` missing version declaration), tell the author what a pinned,
   reproducible environment needs — and, if asked, draft a `renv.lock` / `requirements.txt` /
   Stata `version` + ado manifest for them to review. These are explicit proposals to confirm,
   never silently chosen versions, and nothing is installed or run.

4. Summarize for the author by **priority** (the engine assigns each item P0–P4 by its downstream
   reproducibility cost — you MUST NOT change the assigned priority or kind):
   - **P0** — blocks reproduction; the package will not run as shipped. Fix these first.
   - **P1** — large downstream cost (many fix-loop rounds, coefficient mismatch).
   - **P2** — moderate misread risk for the pipeline/LLM (e.g. `#delimit ;`, loop-built tables).
   - **P3** — minor readability/organization.
   - **P4** — venue compliance / polish only.
   Also distinguish `kind`: **defect** ("this would cost the downstream") vs **normalization**
   ("a better, more standard way to write it — not that your code is wrong"). Line 1 is
   prescriptive, not a fault-finder: most code runs fine; the goal is a package the downstream
   reproduces in one pass. The `references/style_guide.md` explains the normalized forms.

5. Offer the author a tiered plan: "fix P0 only", "P0+P1", or "all". Their next step is to apply
   the changes.

6. Be honest about limits: pre-diagnose **maximizes** the chance of a first-try pass; it does not
   **guarantee** it. Surface the `cannot_predict` list from `risk_register.json`.
