/*
 * changelog-data.js — the single source of truth for the public /changelog page.
 *
 * HOW TO EDIT
 *   Add a new release object at the TOP of `releases` (newest first) and save.
 *   `npm run dev` hot-reloads; `npm run build` ships it. Changelog.jsx only does layout —
 *   it reads every word from this file.
 *
 * WRITE FOR AUTHORS, NOT FOR US.
 *   This is the user-facing changelog. Describe what an author sees and can do:
 *   new commands, new venues, clearer checks. Do NOT paste from core/CHANGELOG.md —
 *   that file is developer-facing and carries internal rule IDs, pipeline terms, and
 *   test counts that should not appear here. Keep the register plain.
 *
 * SHAPE
 *   release = {
 *     version: "0.4.0"  | "Initial release",   // shown as-is; numbers are prefixed "v" by the page
 *     date:    "June 17, 2026",
 *     title:   "one-line theme of the release", // optional
 *     changes: [{ tag: "New" | "Improved" | "Fixed", text: "..." }],
 *   }
 *   In `text`, wrap a `command` or `path` in backticks to render it as monospace code.
 */

export const changelog = {
  head: {
    lead: "What's",
    emphasis: "new",
    sub: "Every ReproAI release, newest first. The plugin's underlying rule set also keeps evolving as more replication packages are seen; run `/reproai:update` to pull the latest.",
  },

  releases: [
    {
      version: "0.5.0",
      date: "June 19, 2026",
      title: "An honest pre-submission checklist, plus three new static checks.",
      changes: [
        {
          tag: "New",
          text: "A clear pre-submission checklist. Venue requirements that reproai cannot confirm by reading your package — signing a form, depositing to a repository, requesting a verification — are now shown as their own \"things to do before you submit\" list, each with what to do, how to do it, how to check you've done it, and the official source. reproai never marks these as passed for you; you complete them.",
        },
        {
          tag: "New",
          text: "A check for a Data Availability Statement: it looks in your README for a statement saying whether the data are public, partly restricted, or not public, and points it out if it's missing.",
        },
        {
          tag: "New",
          text: "A check for data citations: it looks for a persistent identifier (a DOI or handle, or a Dataverse/Zenodo/ICPSR link) so a replicator can fetch the exact data you used.",
        },
        {
          tag: "Improved",
          text: "The reproducible-parallel-results check now reads your R code directly: if a parallel loop draws random numbers without a fixed, reproducible stream, it tells you to switch to doRNG and regenerate the affected tables.",
        },
        {
          tag: "Improved",
          text: "World Bank venue: completes the checklist with the rights statement confirming you had legitimate access to the data, the final manuscript, the paper's tables and figures in raw form, and the expectation that code creates every exhibit and in-text number. Gaps suggested by Mateo Servent (World Bank).",
        },
      ],
    },
    {
      version: "0.4.3",
      date: "June 19, 2026",
      title: "A venue for the World Bank Reproducible Research Repository.",
      changes: [
        {
          tag: "New",
          text: "World Bank venue profile (`worldbank`): the internal reproducibility check World Bank staff and consultants go through before journal submission. It looks for a main script that runs everything after you change only the top-level folder, a README that gives the run order and states the software and version used, a map from each output to the script that makes it, the line(s) to edit to run on another machine, code that starts from the original data, a data availability statement, and the verification request itself. Suggested by Mateo Servent (World Bank).",
        },
      ],
    },
    {
      version: "0.4.2",
      date: "June 19, 2026",
      title: "Contribute back: send lessons and new venues as GitHub issues.",
      changes: [
        {
          tag: "New",
          text: "`/reproai:contribute` turns a lesson into a structured GitHub issue: a defect reproai missed, a false flag, or a journal we don't support yet with its replication rules. reproai never posts on your behalf — it hands you a pre-filled issue to review and submit, and never includes your data, results, or file paths.",
        },
        {
          tag: "New",
          text: "Suggesting a venue: you give the journal's official policy URL and its requirements (each with a verbatim quote); reproai drafts and validates a venue profile, and a maintainer verifies every requirement against the policy before it ships.",
        },
      ],
    },
    {
      version: "0.4.1",
      date: "June 18, 2026",
      title: "A venue for JASA, plus reproducible runs and README tools.",
      changes: [
        {
          tag: "New",
          text: "JASA venue profile (Journal of the American Statistical Association): its README template with a results-to-be-replicated map, the data and code availability form, a master script, the computing environment, a license, and where to deposit the package.",
        },
        {
          tag: "New",
          text: "A check for reproducible parallel results: it flags a parallel loop that draws random numbers without a fixed, reproducible stream, so your bootstrap and simulation numbers come out the same on every run.",
        },
        {
          tag: "Improved",
          text: "README tooling: the checks now read PDF READMEs (not just Markdown), flag duplicate or divergent README files, warn when a README points to a file that is not in the package, and a new helper drafts a README from your package's own structure.",
        },
      ],
    },
    {
      version: "0.4.0",
      date: "June 17, 2026",
      title: "Smoke-testing, and a venue for the Econometric Society.",
      changes: [
        {
          tag: "New",
          text: "`/reproai:debug` trial-runs a copy of your package end to end to confirm it executes and that its tables and figures are actually written. If it hits an error, it explains the cause, offers a few options, and asks how you want to proceed, then re-runs. It only ever touches the copy, and it never judges whether your numbers are correct.",
        },
        {
          tag: "New",
          text: "Econometric Society venue profile, covering Econometrica, Quantitative Economics, and Theoretical Economics.",
        },
        {
          tag: "Improved",
          text: "`/reproai:check` now flags when a reported table or figure is never saved to an output folder, when a multi-script package does not document its run order, and when an intermediate dataset is read by one script but not shipped with the package.",
        },
      ],
    },
    {
      version: "0.3.0",
      date: "June 16, 2026",
      title: "Guided fixes, and five more venues.",
      changes: [
        {
          tag: "New",
          text: "`/reproai:fix` rewrites the recommended changes on a copy of your package, re-checks, and hands you the diff. Only clearly safe edits are applied for you; anything that could change a result is left for you to approve. Your original files are never touched.",
        },
        {
          tag: "New",
          text: "Venue profiles for APSR, AJPS, and JOP, plus generic Harvard Dataverse and openICPSR fallbacks for journals without a dedicated profile.",
        },
        {
          tag: "Improved",
          text: "Stronger detection of deprecated Stata and R syntax that breaks on current software versions, so an old command does not stall a reproducibility run.",
        },
      ],
    },
    {
      version: "Initial release",
      date: "June 15, 2026",
      title: "Static pre-diagnose for replication packages.",
      changes: [
        {
          tag: "New",
          text: "`/reproai:check` scans a working directory, applies the author rule set and a venue profile, and writes a priority-graded advisory, from P0 (blocks reproduction) to P4 (venue polish), of what to fix before you submit. It never runs your code.",
        },
        {
          tag: "New",
          text: "`/reproai:comply` checks a package against a target venue's replication-package rules on its own, without the full pre-diagnose.",
        },
        {
          tag: "New",
          text: "AEA venue profile (AER, AEJ, JEL, JEP), plus a normalized Stata and R style guide. Ships as a plugin for Claude Code and OpenAI Codex.",
        },
      ],
    },
  ],
};
