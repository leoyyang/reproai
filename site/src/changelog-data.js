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
