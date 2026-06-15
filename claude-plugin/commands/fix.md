---
name: reproai-fix
description: Apply the auto-safe (semantics-preserving) subset of reproai's advisory fixes to a COPY of the package. Dry-run by default; never touches the original; never changes what the code computes. Use after /reproai check when the author wants the safe fixes applied automatically.
---

# /reproai fix — apply auto-safe fixes to a copy

reproai only auto-applies fixes that are **provably semantics-preserving** — they cannot change what
the code computes. Everything else stays **propose-only** for you/the author to apply manually after
review. This is deliberate: better to auto-fix nothing than to silently alter a result.

## What is auto-safe (v1)

Only two transforms qualify today:
- **B9** — drop a `quietly` prefix on a `use`/`import` so a missing-file failure becomes visible.
- **B11** — comment out an R Markdown ```{r} fence left in a `.R` file so it parses.

All other advisory items (paths, versions, packages, merges, deprecated syntax, loops, ...) are
**propose-only** — `/reproai fix` will list them but not touch them, because the correct change needs
author knowledge or could change semantics.

## Steps

1. Dry-run first (default — shows a unified diff, writes nothing):

   ```bash
   line1 fix <ROOT> --venue <VENUE>
   ```

2. Review the diff. If it looks right, apply to a **copy** (the original is never modified):

   ```bash
   line1 fix <ROOT> --venue <VENUE> --apply --out <ROOT>_fixed
   ```

   `--out` must not already exist. The original package is left untouched; only the copy is edited.

3. Tell the author which propose-only items remain (from the dry-run output) and walk them through
   those manually — those are the ones that need their judgment.

## Hard rules

- Never apply in place. `--apply` requires `--out`; fixes go to a fresh copy.
- Never auto-apply anything that could change a coefficient, sample, variable, or path resolution.
- The deterministic engine decides eligibility — you do not expand the auto-safe set.
