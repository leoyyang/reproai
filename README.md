# ReproAI — replication-package pre-diagnose (rule set)

ReproAI is a static, no-execution helper that audits a replication package and advises how to make it
cleaner and more reproducible **before** submission. It never runs your code and never judges the
correctness of your results — it points out organization, packaging, and writing-style issues that
commonly make a downstream reproducibility check harder than it needs to be.

Findings are graded **P0–P4** by how much they tend to cost a downstream reproducibility run
(P0 = blocks it; P4 = polish), and tagged **defect** (would cost the pipeline) vs **normalization**
(a more standard way to write it). Auto-safe, semantics-preserving fixes can be applied to a copy;
everything else is propose-only.

These rules distill recurring, **author-preventable** patterns observed across a large body of
replication work. They are generic guidance — no rule names, references, or describes any specific
paper.

- `author_rules.yaml` — the rule set (rules_version 2026.06.16).
- `style_guide.md` — the normalized coding-style reference behind the normalization rules.
