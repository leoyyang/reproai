from __future__ import annotations

from typing import Any

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .dependency_graph import Edge, _INCLUDE_KINDS, _READ_KINDS
from .inventory import FileEntry

_RULES_FILE = Path(__file__).parent / "rules" / "author_rules.yaml"

# B4 absolute path. The UNC branch requires a hostname letter after `\\` so a regex-escape literal
# like gsub("\\|", ...) (two backslashes then a metachar) is no longer mistaken for a UNC path.
_ABS_PATH = re.compile(r'["\']?((?:[A-Za-z]:\\|\\\\[A-Za-z]|/Users/|/home/|~/)[^"\'\r\n]+)["\']?')
_ABS_TARGET = re.compile(r'^\s*(?:[A-Za-z]:\\|\\\\|/|~)')
_LOOP_HEAD = re.compile(r'^\s*(foreach|forvalues|forv|while|for)\b', re.IGNORECASE)
_EXPORT_FIXED = re.compile(r'\b(esttab|estout|outreg2?|putexcel|tabout)\b[^\r\n]*using\s+["\']?([^\s"\'`,]+)', re.IGNORECASE)
_TS_OP = re.compile(r'(?<![\w.])([LDF]\d*\.\w+)')
_TSSET = re.compile(r'^\s*(tsset|xtset)\b', re.IGNORECASE | re.MULTILINE)
# Allow common Stata prefixes before the estimator: `xi:`, `by/bysort ... :`, `quietly`,
# `capture`, `noisily`, `svy:` — otherwise `xi: reg ...` / `bysort y: reg ...` are missed.
_STATA_PREFIX = r'(?:(?:cap(?:ture)?|qui(?:etly)?|noi(?:sily)?|xi|svy|eststo(?:\s+\w+)?|est(?:imates)?\s+sto(?:re)?(?:\s+\w+)?|estpost|by(?:sort)?\s+[^\r\n:]+)[\s:]+)*'
_ESTIMATION = re.compile(r'^\s*' + _STATA_PREFIX + r'(reg|regress|areg|xtreg|reghdfe|ivreg\w*|ivregress|logit|probit|tobit|glm|xtivreg\w*|melogit|mlogit)\b', re.IGNORECASE | re.MULTILINE)
# R estimators are almost always ASSIGNED (m <- lm(...), fit = ivreg(...)) so the verb is not at
# line start; match an optional `name <-`/`name =` then a known R estimator call.
_R_ESTIMATION = re.compile(r'(?:^|<-|=|\(|\s)\s*(lm|glm|lm_robust|iv_robust|ivreg|ivreg2|felm|feols|feglm|plm|lmer|glmer|polr|multinom|gam|coxph|survreg|rdrobust|rdd_reg)\s*\(', re.IGNORECASE)
_DATA_LOAD_STATA = re.compile(r'^\s*(use|import|insheet|infile|odbc)\b', re.IGNORECASE | re.MULTILINE)
_DATA_LOAD_R = re.compile(r'\b(read\.|read_|load\(|readRDS\(|fread\()', re.MULTILINE)
_GITHUB_INSTALL = re.compile(r'(install_github|pip install\s+git\+|remotes::install)', re.IGNORECASE)
_INSTALL_NOPIN = re.compile(r'^\s*(install\.packages|library|require)\b', re.IGNORECASE | re.MULTILINE)
_CLEAR_ALL = re.compile(r'^\s*clear\s+all\b', re.IGNORECASE | re.MULTILINE)
_VERSION_STMT = re.compile(r'^\s*version\s+\d', re.IGNORECASE | re.MULTILINE)
_VERSION_SENSITIVE = re.compile(r'\b(reghdfe|rdrobust|ivreghdfe|did2s|csdid|ivregress|ivreg2?|xtivreg\w*)\b', re.IGNORECASE)
_WIDE_WILDCARD = re.compile(r'\bi\.\w+\#i?\.\w+|\b\w+\*(?:\s|,|$)')

_CAPTURE_USE = re.compile(r'^\s*(?:cap(?:ture)?|qui(?:etly)?|noi(?:sily)?)[\s:]+(?:.*?\s)?use\s+"?([^"\r\n,]+?\.dta)"?', re.IGNORECASE)
_RC_GUARD = re.compile(r'^\s*if\s+_rc\b', re.IGNORECASE)
_GUARD_USE = re.compile(r'\buse\s+"?([^"\r\n,]+?\.dta)"?', re.IGNORECASE)
_R_TABLE_CALL = re.compile(r'\b(stargazer|xtable|print\.xtable|texreg|htmlreg|screenreg)\s*\(', re.IGNORECASE)
_STATA_DROP = re.compile(r'^\s*drop\s+(.+)$', re.IGNORECASE)
_STATA_KEEP = re.compile(r'^\s*keep\s+(.+)$', re.IGNORECASE)
_STATA_RENAME = re.compile(r'^\s*rename?\s+(\w+)\s+(\w+)', re.IGNORECASE)
_DATA_REF = re.compile(r'^\s*(?:cap(?:ture)?\s+|qui(?:etly)?\s+|noi(?:sily)?\s+)*(use|import\s+delimited|insheet|infile)\s+(?:using\s+)?"?([^",\r\n]+?)"?\s*(?:,|$)', re.IGNORECASE)
_REL_CD = re.compile(r'^\s*cd\s+"?(?![A-Za-z]:\\|\\\\|/|~)([^"\r\n]+)"?', re.IGNORECASE)
_QUIET_LOAD = re.compile(r'^\s*(?:qui(?:etly)?[: ]).*\b(use|import|insheet|infile)\b', re.IGNORECASE)
_TABLE_C = re.compile(r'^\s*table\s+\w[^,\r\n]*,\s*c\(', re.IGNORECASE)
_TMPDIR = re.compile(r'\btmpdir\b', re.IGNORECASE)
_RDROBUST_DEPR = re.compile(r'\brdrobust\b[^\r\n]*bwselect\((?:CCT|IK)\)', re.IGNORECASE)
_REGHDFE_IV = re.compile(r'\breghdfe\b[^\r\n]*\([^)=\r\n]+=[^)\r\n]+\)', re.IGNORECASE)
_LEGACY_MIXED = re.compile(r'^\s*(?:xi:\s*)?(xtmelogit|xtmepoisson|meqrlogit|meqrpoisson|xtmixed)\b', re.IGNORECASE)
_CD_EMPTY = re.compile(r'^\s*cd\s+""\s*$', re.IGNORECASE)
_OLD_MERGE = re.compile(r'^\s*merge\s+(?![0-9m]+\s*:\s*[0-9m]+)([A-Za-z_]\w*)\b[^\r\n]*\busing\b', re.IGNORECASE)
_DEPRECATED_R_PKG = re.compile(r'\blibrary\s*\(\s*["\']?(rgdal|rgeos|maptools|ZeligMultilevel|Zelig|checkpoint|hrbrthemes|arm)\b', re.IGNORECASE)
# C7: non-reproducible parallel RNG. `%dopar%` advances a fresh stream per worker;
# doRNG (`%dorng%` or `registerDoRNG(seed)`) is what makes the loop reproducible.
_PAR_DOPAR = re.compile(r'%dopar%')
_PAR_REPRO = re.compile(r'%dorng%|registerDoRNG', re.IGNORECASE)
_RMD_CHUNK = re.compile(r'^\s*```\s*\{[rR]')
_R_IN_DO = re.compile(r'(\blibrary\s*\([A-Za-z]|\b\w+\s*<-\s|\bcollin\b)')
_KNOWN_USER_ADO = {
    "combomarginsplot", "coefplot", "winsor2", "binscatter", "grstyle", "xtabond2",
    "ranktest", "weakivtest", "boottest", "psmatch2", "kmatch", "synth", "eventdd",
    "parmest", "parmby", "spmap", "edvreg", "xtqmlp", "ivreg2", "ivreghdfe", "xtivreg2",
    "csdid", "did2s", "drdid", "rangestat", "carryforward", "mdesc", "fre", "estout", "outreg2",
}
_INSTALL_ADO = re.compile(r'\b(?:ssc\s+install|net\s+install|findit)\s+(\w+)', re.IGNORECASE)
_CMD_HEAD = re.compile(r'^\s*(?:cap(?:ture)?\s+|qui(?:etly)?\s+|noi(?:sily)?\s+|xi:\s*)*([a-z]\w+)', re.IGNORECASE)
_COMMENTED_REG = re.compile(r'^\s*(?:\*|//)\s*(reg|regress|areg|xtreg|reghdfe|ivreg\w*|ivregress|ivreghdfe|logit|probit|tobit)\b', re.IGNORECASE)
_RESTRICTED_WORD = re.compile(r'restrict|confidential|propriet|not\s+public|non-public|unavailable|cannot\s+share|under\s+embargo', re.IGNORECASE)
_DATA_EXTS = (".dta", ".tab", ".csv", ".rds", ".rdata", ".xlsx", ".parquet")
_DELIMIT = re.compile(r'^\s*#delimit\s*;|^\s*#d\s*;', re.IGNORECASE)
_R_TABLE_CALL_LONG = re.compile(r'\b(stargazer|xtable|texreg|htmlreg|screenreg)\s*\(', re.IGNORECASE)
_PROGRAM_DEF = re.compile(r'^\s*program\s+(?:define\s+)?(\w+)', re.IGNORECASE)

# D1 artifact-output coverage
_TABLE_EXPORT = re.compile(r'\b(esttab|estout|outreg2?|putexcel|putdocx|tabout|stargazer|texreg|htmlreg|etable|modelsummary|write[._]csv|write[._]dta|saveRDS|export\s+delimited)\b', re.IGNORECASE)
# Follow-up A: a figure producer may be ASSIGNED (`p <- ggplot(...)`, `g = qplot(...)`), which the
# old `^\s*`-anchored pattern missed entirely. The optional assignment prefix
# `(?:[\w.$]+\s*(?:<-|<<-|=)\s*)?` admits `name <-`/`name <<-`/`name =` before the producer while the
# trailing producer alternation still gates (so `x <- mean(y)` does NOT match). Widening this makes
# D1/gate STRICTER (an assigned plot now expects an export), so only HIGH-CONFIDENCE producers were
# added: R `qplot(`/`autoplot(`. Base-R `hist(`/`boxplot(`/`barplot(`/`image(`/`contour(` were
# DEFERRED — they fire on incidental diagnostic plots (false-positive risk); Stata `saving()` graph
# option DEFERRED (ambiguous, appears in non-graph contexts).
_GRAPH_CMD = re.compile(r'^\s*(?:[\w.$]+\s*(?:<-|<<-|=)\s*)?(graph\s+(?:twoway|bar|box|matrix|combine|tw)|twoway|histogram|scatter|kdensity|coefplot|marginsplot|ggplot|qplot|autoplot|plot\()', re.IGNORECASE)
# A figure write-out: a graphics device open or an explicit graph-export verb. Single leading `\b`
# (NOT per-token) is deliberate — a per-token `\b` would false-match `foo.png(`. `(` is escaped.
# Kept a strict superset of the graphics-device subset of dependency_graph._WRITE_VERBS; the
# drift-guard test (test_graph_export_covers_dependency_graph_devices) fails CI if that ever breaks.
_GRAPH_EXPORT = re.compile(
    r'\b(graph\s+export|graph\s+save|ggsave|gr\s+export|dev\.copy|'
    r'pdf\(|png\(|jpe?g\(|tiff\(|bmp\(|svg\(|svglite\(|'
    r'cairo_pdf\(|cairo_ps\(|bitmap\(|'
    r'agg_png\(|agg_jpe?g\(|agg_tiff\(|'
    r'Cairo\(|CairoPNG\(|CairoPDF\(|CairoJPEG\(|CairoTIFF\(|'
    r'tikz\(|postscript\(|savefig\()',
    re.IGNORECASE)
# D3 intermediate data write / read
_DATA_WRITE = re.compile(r'^\s*(?:cap(?:ture)?\s+|qui(?:etly)?\s+)*(save|saveold|export\s+delimited|outsheet|saveRDS|write[._]csv|write[._]dta|write[._]rds|haven::write_dta|saveRDS)\b[^\r\n]*?["\']?([\w./\\-]+\.(?:dta|csv|rds|rdata|tab|parquet))["\']?', re.IGNORECASE)
_FILE_EXISTS_GUARD = re.compile(r'(confirm\s+file|file\.exists|os\.path\.exists|assert\s+_rc|fileexists)', re.IGNORECASE)
# D1 table/figure section headers in comments (e.g. "* Table 3: ..." / "# Figure 2" / "# --> Table 1").
# The optional `(?:[-=]{1,2}>\s*)?` slot accepts the `-->`/`->`/`=>` anchor reproai itself recommends
# (A12/D1/A2 target_form), while the 1-2 char arrow-body rejects long arrows (`---->`), bullets
# (`# - Table`), and hrules (`# ----`). See test_table_header_matches_recommended_anchor.
#
# Follow-up B: the number group `_NUM_LABEL` captures the FULL label, not a truncated prefix.
#   - `[A-Za-z]{0,3}[-.]?` — appendix/SI prefixes: `A.1`, `E1`, `S1`, `SI-3`, `B2a` (1-3 letters,
#     optional `-`/`.` separator). 1-3 letters is deliberate: it admits `SI` but not whole words.
#   - `\d+(?:[.\-]\d+)*` — multi-segment numbers: `1`, `1.2`, `1-2`, `1.2.3`. This FIXES the old
#     `([A-Za-z]?\.?\d+)` silent partial-match where `Table 1.2` captured only `1`, MERGING
#     sub-tables 1.1 and 1.2 into one `_section_spans` group. They are now DISTINCT spans.
#   - `[a-z]?` — a trailing sub-table letter: `1a`, `B2a`.
# Known limitation: Roman-numeral labels (`Table II`) are not captured (rare; documented, not fixed).
_NUM_LABEL = r'([A-Za-z]{0,3}[-.]?\d+(?:[.\-]\d+)*[a-z]?)'
_TABLE_HEADER = re.compile(r'^\s*(?:\*+|//+|#+)\s*\**\s*(?:[-=]{1,2}>\s*)?\**\s*(Table|Tabla)\s+' + _NUM_LABEL + r'\b', re.IGNORECASE)
_FIGURE_HEADER = re.compile(r'^\s*(?:\*+|//+|#+)\s*\**\s*(?:[-=]{1,2}>\s*)?\**\s*(Figure|Fig\.?|Figura)\s+' + _NUM_LABEL + r'\b', re.IGNORECASE)

# C8: stochastic operation with no seed (the generalization of C7, which owns the parallel %dopar%
# case). A seed FIXES the realized draws, so this is output-changing, not lossless.
_R_STOCHASTIC = re.compile(
    r'(?<![\w.])(sample|sample_n|slice_sample|rnorm|runif|rbinom|rpois|rbeta|rgamma|rexp|'
    r'rmultinom|rnbinom|rcauchy|rweibull|rchisq|rt|boot|amelia|mice)\s*\(', re.IGNORECASE)
_R_SEED_SIGNAL = re.compile(
    r'set\.seed\s*\(|registerDoRNG|%dorng%|clusterSetRNGStream|future\.seed\s*=|RNGkind\s*\(', re.IGNORECASE)
_R_FUTURE_BACKEND = re.compile(r'\bfurrr\b|\bfuture_(?:map|lapply|apply|walk)\b|%<-%|\bfuture\s*\(', re.IGNORECASE)
_R_PARALLEL_BACKEND = re.compile(r'mclapply|makeCluster|parLapply|mcmapply|mcsapply', re.IGNORECASE)
_STATA_STOCHASTIC = re.compile(
    r'(?<![\w.])(bootstrap|bsample|permute|simulate)\b|runiform\s*\(|rnormal\s*\(|'
    r'rbinomial\s*\(|rpoisson\s*\(|rgamma\s*\(|rbeta\s*\(', re.IGNORECASE)
_STATA_SEED = re.compile(r'\bset\s+seed\b|\bset\s+rngstream\b', re.IGNORECASE)

# D7: variables used in estimation but absent from a shipped codebook. Tolerant, advisory, never P0.
_CODEBOOK_NAME = re.compile(
    r'codebook|data[\s_-]?dictionar|variable[\s_-]?(?:list|definition|description|name)|var[\s_-]?list|datadict',
    re.IGNORECASE)
_CODEBOOK_EXT = {".md", ".txt", ".tex", ".csv", ".rst"}
_VAR_TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_]{2,}')
_STATA_EST_VARLIST = re.compile(
    r'^\s*' + _STATA_PREFIX + r'(?:reg|regress|areg|xtreg|reghdfe|ivreg\w*|ivregress|ivreghdfe|'
    r'logit|probit|tobit|glm|xtivreg\w*|melogit|mlogit|poisson|nbreg|xtpoisson)\s+([^,\r\n]+)',
    re.IGNORECASE | re.MULTILINE)
_STATA_FACTOR_PREFIX = re.compile(r'\b[ibco]*\d*\.(\w+)', re.IGNORECASE)
_R_FORMULA = re.compile(r'([A-Za-z_.][\w.]*)\s*~\s*([^,\)\r\n]+)')
_VAR_STOP = {
    "using", "cluster", "robust", "vce", "absorb", "weight", "weights", "fweight", "pweight",
    "aweight", "iweight", "subset", "data", "factor", "log", "exp", "sqrt", "poly", "true",
    "false", "null", "and", "the", "for", "with",
}


@dataclass
class Finding:
    rule_id: str
    category: str
    kind: str
    priority: str
    message: str
    evidence: list[dict[str, Any]]
    rationale: str
    source_lessons: list[str]
    why_downstream: str = ""
    target_form: str = ""
    lossless_note: str = ""
    propose_only: bool = False
    output_changing: bool = False


def load_rules() -> list[dict[str, Any]]:
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8"))["rules"]


def _texts(root: Path, entries: list[FileEntry]) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in entries:
        if entry.language in {"stata", "r", "python"}:
            try:
                out[entry.path] = (root / entry.path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                out[entry.path] = ""
    return out


def _ev(path: str, line: int | None = None, snippet: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"file": path}
    if line is not None:
        item["line"] = line
    if snippet is not None:
        item["snippet"] = snippet.strip()[:200]
    return item


def _lang_of(entries: list[FileEntry], path: str) -> str:
    for e in entries:
        if e.path == path:
            return e.language
    return "other"


# --- Comment-aware line scanning (FIX: B4 and the line-by-line detector class false-firing in comments) -
# The defective callers below scan for CODE patterns (abs paths, time-series ops, wildcards, GitHub
# installs, ...). A path/pattern left inside a `#`/`*`/`//` comment — including by reproai's OWN /fix
# output (`# was: setwd("/Users/...")`) — must NOT fire. The hard constraint: we must strip the
# COMMENT while PRESERVING string literals, because _ABS_PATH reads a path *inside a quoted string*
# (`setwd("/abs")`). Blanking string contents (the rejected _mask_r_strings_comments approach) would
# make B4 catch nothing on its real case. Technique: mask only string *contents* in a throwaway copy
# to locate the first UNQUOTED comment marker, then slice the ORIGINAL line there so strings survive.
_STR_SPAN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def _mask_string_contents(line: str, lang: str = "r") -> str:
    """Replace the *contents* of every complete string literal with same-length filler (keeping the
    delimiters and length), so comment markers inside strings are hidden but column indices are
    unchanged. An unterminated string masks to end-of-line (a `#`/`//` after an open quote is still
    inside it).

    Language-aware string syntax:
    - R / Python: both `"..."` and `'...'` are strings.
    - Stata: ONLY `"..."` and the compound `` `"..."' `` form are strings. A bare `'` is macro-close
      syntax (`` `macro' ``), NOT a string delimiter, so it must NOT open a masked span — otherwise an
      odd number of macro apostrophes before an inline `//` masks the comment marker away."""
    if lang == "stata":
        return _mask_string_contents_stata(line)
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in '"\'':
            m = _STR_SPAN.match(line, i)
            if m:
                out.append(ch + ("x" * (m.end() - i - 2)) + ch)
                i = m.end()
                continue
            # unterminated literal: mask the rest of the line as string interior
            out.append(ch + ("x" * (n - i - 1)))
            break
        out.append(ch)
        i += 1
    return "".join(out)


def _mask_string_contents_stata(line: str) -> str:
    """Stata variant of _mask_string_contents. Strings are `"..."` and compound `` `"..."' ``; a bare
    `'` is a macro close, never a string delimiter, so it is emitted verbatim (leaving any following
    `//` comment marker visible)."""
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        # compound double-quote string: `" ... "'
        if line.startswith('`"', i):
            close = line.find('"\'', i + 2)
            if close == -1:  # unterminated -> mask to EOL
                out.append('`"' + ("x" * (n - i - 2)))
                break
            out.append('`"' + ("x" * (close - (i + 2))) + '"\'')
            i = close + 2
            continue
        ch = line[i]
        if ch == '"':  # simple double-quote string
            close = line.find('"', i + 1)
            if close == -1:  # unterminated -> mask to EOL
                out.append('"' + ("x" * (n - i - 1)))
                break
            out.append('"' + ("x" * (close - i - 1)) + '"')
            i = close + 1
            continue
        out.append(ch)  # backtick, apostrophe, and everything else: literal (NOT a string)
        i += 1
    return "".join(out)


def _strip_comment_keep_strings(line: str, lang: str) -> str:
    """Return the CODE portion of one physical line: comment removed, string literals intact.

    R / Python: `#` (only when unquoted).
    Stata (.do/.ado): a line-leading `*` (whole line is a comment), an inline `//` (unquoted), and a
    single-line `/* ... */` (the spanned region). Multi-line `/* */` blocks across physical lines are
    a noted limitation — left intact.
    Unknown languages: returned unchanged (no false-negative risk for non-script file types)."""
    masked = _mask_string_contents(line, lang)
    if lang == "stata":
        # whole-line comment: first non-whitespace char is `*`
        stripped = masked.lstrip()
        if stripped.startswith("*"):
            return line[: len(line) - len(stripped)]  # keep leading whitespace only
        # single-line /* ... */ (remove every same-line balanced span; ignore unterminated openers)
        while True:
            open_i = masked.find("/*")
            if open_i == -1:
                break
            close_i = masked.find("*/", open_i + 2)
            if close_i == -1:
                break  # opener with no same-line closer -> multi-line; leave as-is (noted limitation)
            line = line[:open_i] + " " * (close_i + 2 - open_i) + line[close_i + 2 :]
            masked = masked[:open_i] + " " * (close_i + 2 - open_i) + masked[close_i + 2 :]
        # inline // comment (unquoted)
        slash = masked.find("//")
        if slash != -1:
            return line[:slash]
        return line
    if lang in {"r", "python"}:
        hash_i = masked.find("#")
        if hash_i != -1:
            return line[:hash_i]
        return line
    return line


def _code_line_hits(text: str, regex: re.Pattern[str], lang: str) -> list[tuple[int, str]]:
    """Per-line regex scan that matches `regex` against the comment-stripped CODE portion of each line
    (string literals preserved) while RETURNING the original line and its real 1-based line number,
    so evidence still shows the true source line."""
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        if regex.search(_strip_comment_keep_strings(line, lang)):
            hits.append((i, line))
    return hits


def _upstream_loads_data(path: str, edges: list[Edge], texts: dict[str, str], loader: re.Pattern[str]) -> bool:
    parents = [e.src for e in edges if e.kind in {"do", "source"} and e.resolved and e.dst == path]
    for parent in parents:
        ptext = texts.get(parent, "")
        marker = f'"{Path(path).name}"'
        idx = ptext.find(Path(path).name)
        prefix = ptext[:idx] if idx != -1 else ptext
        if loader.search(prefix):
            return True
        if _upstream_loads_data(parent, edges, texts, loader):
            return True
    return False


def _detect_guarded_fallback(root: Path, path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        m = _CAPTURE_USE.search(line)
        if not m:
            continue
        file_a = m.group(1).strip()
        for j in range(i + 1, min(i + 4, len(lines))):
            if _RC_GUARD.search(lines[j]):
                block = "\n".join(lines[j:j + 6])
                gm = _GUARD_USE.search(block)
                if gm:
                    file_b = gm.group(1).strip()
                    a_exists = (root / Path(file_a).name).exists() or any(p.name == Path(file_a).name for p in root.rglob(Path(file_a).name))
                    b_exists = (root / Path(file_b).name).exists() or any(p.name == Path(file_b).name for p in root.rglob(Path(file_b).name))
                    if a_exists and b_exists and Path(file_a).name != Path(file_b).name:
                        hits.append(_ev(path, i + 1, line))
                break
    return hits


def _mask_r_strings_comments(s: str) -> str:
    out = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
    out = re.sub(r"'(?:\\.|[^'\\])*'", "''", out)
    out = re.sub(r'#.*', '', out)
    return out


_R_ORPHAN_ARG = re.compile(r'^\s*[A-Za-z_][\w.]*\s*=')


def _detect_r_table_syntax(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not _R_TABLE_CALL.search(line):
            continue
        window = lines[i:i + 40]
        depth = 0
        started = False
        balanced_at = None
        went_negative = False
        for k, w in enumerate(window):
            masked = _mask_r_strings_comments(w)
            for ch in masked:
                if ch == "(":
                    depth += 1
                    started = True
                elif ch == ")":
                    depth -= 1
                    if started and depth < 0:
                        went_negative = True
            if started and depth <= 0:
                balanced_at = k
                break
        if started and balanced_at is None:
            hits.append(_ev(path, i + 1, line))
            continue
        if went_negative:
            hits.append(_ev(path, i + 1, line))
            continue
        if started and balanced_at is not None:
            for w in window[balanced_at + 1: balanced_at + 3]:
                masked = _mask_r_strings_comments(w).strip()
                if _R_ORPHAN_ARG.match(masked):
                    hits.append(_ev(path, i + 1 + balanced_at, w))
                    break
    return hits


def _detect_lifecycle_contradiction(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    dropped: dict[str, int] = {}
    renamed_away: dict[str, int] = {}
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        dm = _STATA_DROP.match(line)
        if dm:
            for v in re.findall(r'\b[A-Za-z_]\w*\b', dm.group(1)):
                dropped[v] = i
            continue
        rn = _STATA_RENAME.match(line)
        if rn:
            renamed_away[rn.group(1)] = i
            dropped.pop(rn.group(2), None)
            renamed_away.pop(rn.group(2), None)
            continue
        gen = re.match(r'^\s*(?:gen(?:erate)?|egen|clonevar|recode)\b.*?\b([A-Za-z_]\w*)\s*=', line, re.IGNORECASE)
        if gen:
            dropped.pop(gen.group(1), None)
            renamed_away.pop(gen.group(1), None)
        if _ESTIMATION.match(line):
            for v in re.findall(r'\b[A-Za-z_]\w*\b', line):
                if v in dropped:
                    hits.append(_ev(path, i, f"uses '{v}' dropped at line {dropped[v]}: {line.strip()[:120]}"))
                elif v in renamed_away:
                    hits.append(_ev(path, i, f"uses '{v}' renamed away at line {renamed_away[v]}: {line.strip()[:120]}"))
    return hits


def _shipped_stems(root: Path) -> dict[str, list[str]]:
    stems: dict[str, list[str]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in _DATA_EXTS:
            stems.setdefault(path.stem.lower(), []).append(path.name)
    return stems


def _detect_data_ref_mismatch(root: Path, path: str, text: str, stems: dict[str, list[str]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = _DATA_REF.match(line)
        if not m:
            continue
        target = m.group(2).strip().replace("\\", "/")
        name = Path(target).name
        stem = Path(name).stem.lower()
        suffix = Path(name).suffix.lower()
        resolved = (root / name).exists() or any(p.name == name for p in root.rglob(name))
        if resolved:
            continue
        shipped = stems.get(stem)
        if shipped and (not suffix or all(Path(s).suffix.lower() != suffix for s in shipped)):
            hits.append(_ev(path, i, f"references '{name}' but package ships {shipped}"))
    return hits


def _detect_relative_cd(path: str, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _REL_CD.match(line):
            hits.append(_ev(path, i, line))
    return hits


def _detect_compat_signatures(path: str, text: str, has_version: bool) -> list[dict[str, Any]]:
    # Follow-up C: every scanner here is comment-blind unless it reads the comment-stripped CODE
    # portion. `_detect_compat_signatures` is only ever called on Stata (.do/.ado) — see the
    # `if lang == "stata":` dispatch — so strip with lang="stata". A commented `tmpdir`
    # (`* note: tmpdir` / `// tmpdir`) or any of the other commented signatures must stay silent,
    # while real code still fires. Evidence snippets keep the ORIGINAL line.
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        code = _strip_comment_keep_strings(line, "stata")
        if _REGHDFE_IV.search(code):
            hits.append(_ev(path, i, f"reghdfe IV-syntax (use ivreghdfe or pin version): {line.strip()[:90]}"))
        elif _RDROBUST_DEPR.search(code):
            hits.append(_ev(path, i, f"rdrobust deprecated bwselect(): {line.strip()[:90]}"))
        elif _TABLE_C.match(code):
            hits.append(_ev(path, i, f"`table var, c(...)` removed in Stata 17: {line.strip()[:90]}"))
        elif _TMPDIR.search(code) and not has_version:
            hits.append(_ev(path, i, f"tmpdir needs Stata 17+; declare version: {line.strip()[:90]}"))
        elif _LEGACY_MIXED.match(code):
            hits.append(_ev(path, i, f"legacy mixed-model command (hangs/removed on modern Stata; use me-prefix): {line.strip()[:90]}"))
        elif _CD_EMPTY.match(code):
            hits.append(_ev(path, i, "`cd \"\"` switches to HOME and breaks relative data paths"))
    return hits


def _detect_old_merge(path: str, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _OLD_MERGE.match(line):
            hits.append(_ev(path, i, line))
    return hits


def _detect_deprecated_r_pkg(path: str, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m = _DEPRECATED_R_PKG.search(line)
        if m:
            hits.append(_ev(path, i, f"{m.group(1)} is removed/deprecated and halts the script if loaded"))
    return hits


def _detect_nonreproducible_parallel_rng(path: str, text: str) -> list[dict[str, Any]]:
    masked = _mask_r_strings_comments(text)
    if not _PAR_DOPAR.search(masked) or _PAR_REPRO.search(masked):
        return []
    for i, line in enumerate(text.splitlines(), start=1):
        if _PAR_DOPAR.search(_mask_r_strings_comments(line)):
            return [_ev(path, i, line)]
    return []


def _detect_unseeded_stochastic(path: str, text: str, lang: str) -> list[dict[str, Any]]:
    if lang == "r":
        masked = _mask_r_strings_comments(text)
        if _PAR_DOPAR.search(masked):
            return []  # the parallel %dopar% case is C7's, not C8's
        if _R_SEED_SIGNAL.search(masked) or not _R_STOCHASTIC.search(masked):
            return []
        if _R_FUTURE_BACKEND.search(masked):
            hint = "future/furrr backend: set future.seed = TRUE (or a seed)"
        elif _R_PARALLEL_BACKEND.search(masked):
            hint = "parallel backend: RNGkind(\"L'Ecuyer-CMRG\") then set.seed(N)"
        elif re.search(r'(?<![\w.])amelia\s*\(', masked, re.IGNORECASE):
            hint = "Amelia: pass the seed= argument"
        elif re.search(r'(?<![\w.])mice\s*\(', masked, re.IGNORECASE):
            hint = "mice: pass the seed= argument"
        else:
            hint = "serial draw: set.seed(N) before the first draw"
        for i, line in enumerate(text.splitlines(), start=1):
            if _R_STOCHASTIC.search(_mask_r_strings_comments(line)):
                return [_ev(path, i, f"stochastic draw with no seed set --- {hint}")]
        return []
    # stata
    if _STATA_SEED.search(text) or not _STATA_STOCHASTIC.search(text):
        return []
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("*") or stripped.startswith("//"):
            continue
        if _STATA_STOCHASTIC.search(line):
            return [_ev(path, i, "stochastic command with no `set seed` --- set seed N (set rngstream under parallel)")]
    return []


def _used_variables(text: str, lang: str) -> set[str]:
    used: set[str] = set()
    if lang == "stata":
        for m in _STATA_EST_VARLIST.finditer(text):
            varlist = _STATA_FACTOR_PREFIX.sub(r'\1', m.group(1))
            used |= {t.lower() for t in _VAR_TOKEN.findall(varlist)}
    elif lang == "r":
        for m in _R_FORMULA.finditer(text):
            for side in (m.group(1), m.group(2)):
                cleaned = re.sub(r'[A-Za-z_.][\w.]*\s*\(', ' ', side)  # drop function-call heads, keep their args
                used |= {t.lower() for t in _VAR_TOKEN.findall(cleaned)}
    return used


def _detect_codebook_coverage(root: Path, entries: list[FileEntry], texts: dict[str, str]) -> list[dict[str, Any]]:
    cb_text: str | None = None
    cb_path: str | None = None
    for e in entries:
        name = Path(e.path).name
        if _CODEBOOK_NAME.search(name) and Path(name).suffix.lower() in _CODEBOOK_EXT:
            try:
                cb_text = (root / e.path).read_text(encoding="utf-8", errors="replace").lower()
                cb_path = e.path
                break
            except OSError:
                continue
    if cb_text is None:  # no readable codebook -> D7 is silent (D4 owns "no documentation at all")
        return []
    used: set[str] = set()
    for path, text in texts.items():
        used |= _used_variables(text, _lang_of(entries, path))
    undocumented = sorted(v for v in used if v not in _VAR_STOP and v not in cb_text)
    if not undocumented:
        return []
    return [_ev(cb_path, None,
                f"{len(undocumented)} analysis variable(s) absent from the codebook: {', '.join(undocumented[:12])}")]


def _detect_rmd_chunk(path: str, text: str) -> list[dict[str, Any]]:
    for i, line in enumerate(text.splitlines(), start=1):
        if _RMD_CHUNK.match(line):
            return [_ev(path, i, line)]
    return []


def _detect_embedded_foreign(path: str, text: str) -> list[dict[str, Any]]:
    est = _ESTIMATION.search(text)
    cutoff = est.start() if est else len(text)
    head = text[:cutoff]
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(head.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("*") or stripped.startswith("//"):
            continue
        if _R_IN_DO.search(line):
            hits.append(_ev(path, i, line))
            break
    return hits


def _detect_unvendored_ado(root: Path, path: str, text: str) -> list[dict[str, Any]]:
    shipped_ado = {p.stem.lower() for p in root.rglob("*.ado")}
    declared = {m.lower() for m in _INSTALL_ADO.findall(text)}
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("*") or stripped.startswith("//"):
            continue
        m = _CMD_HEAD.match(line)
        if not m:
            continue
        cmd = m.group(1).lower()
        if cmd in _KNOWN_USER_ADO and cmd not in shipped_ado and cmd not in declared and cmd not in seen:
            seen.add(cmd)
            hits.append(_ev(path, i, f"uses user-written '{cmd}' (not base Stata, no .ado shipped, no ssc install)"))
    return hits


def _detect_commented_restricted(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not _COMMENTED_REG.match(line):
            continue
        window = "\n".join(lines[max(0, i - 3): i + 4])
        if _RESTRICTED_WORD.search(window):
            hits.append(_ev(path, i + 1, line))
    return hits


def _detect_delimit(path: str, text: str) -> list[dict[str, Any]]:
    for i, line in enumerate(text.splitlines(), start=1):
        if _DELIMIT.match(line):
            return [_ev(path, i, line)]
    return []


def _detect_long_r_table_call(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not _R_TABLE_CALL_LONG.search(line):
            continue
        depth = 0
        started = False
        span = 0
        for w in lines[i:i + 60]:
            masked = _mask_r_strings_comments(w)
            for ch in masked:
                if ch == "(":
                    depth += 1
                    started = True
                elif ch == ")":
                    depth -= 1
            span += 1
            if started and depth <= 0:
                break
        if span > 15:
            hits.append(_ev(path, i + 1, f"{line.strip()[:60]} ... spans {span} lines"))
    return hits


def _detect_wrapper_estimation(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    in_program = None
    depth = 0
    for i, line in enumerate(lines, start=1):
        pm = _PROGRAM_DEF.match(line)
        if pm:
            in_program = pm.group(1)
            continue
        if in_program and re.match(r'^\s*end\b', line):
            in_program = None
            continue
        if in_program and _ESTIMATION.match(line):
            hits.append(_ev(path, i, f"estimation inside program '{in_program}': {line.strip()[:90]}"))
    return hits


def _is_estimation(line: str) -> bool:
    return bool(_ESTIMATION.match(line) or _R_ESTIMATION.search(line))


def _toplevel_estimation_lines(text: str) -> list[int]:
    """1-based line numbers of estimations NOT inside an R function body or a Stata program.
    A pure helper library (only functions defining estimations) is not an analysis script."""
    out: list[int] = []
    brace_depth = 0
    in_stata_program = False
    for i, line in enumerate(text.splitlines(), start=1):
        if _PROGRAM_DEF.match(line):
            in_stata_program = True
        elif in_stata_program and re.match(r'^\s*end\b', line):
            in_stata_program = False
        if not in_stata_program and brace_depth == 0 and _is_estimation(line):
            out.append(i)
        masked = _mask_r_strings_comments(line)
        brace_depth += masked.count("{") - masked.count("}")
        if brace_depth < 0:
            brace_depth = 0
    return out


def _has_toplevel_estimation(text: str) -> bool:
    return len(_toplevel_estimation_lines(text)) > 0


# A table/figure export only counts for D1 if it writes under a designated `tables/`/`figures/`
# subfolder — same rule as `reproai gate`, so `reproai check` (D1) and the gate agree on what is
# "exported". Keep this in lockstep with gate._OUT_TABLE/_OUT_FIGURE and the inline target-extractor
# in gate._section_export_targets.
#
# Follow-up D (recommend≡detect): D1's `rule` advises "a designated relative output folder (e.g.
# output/tables, output/figures)", but the detector hard-required the literal `output/` prefix, so
# `results/tables/`, `tables/`, etc. failed. The optional `(?:[\w.\-]+[\\/])*` prefix now accepts any
# (or no) leading path before the `tables/`/`figures/` segment, so `output/tables/`,
# `results/tables/`, and bare `tables/` all satisfy the intent. The `tables/`/`figures/` SEGMENT is
# still required, so the misnamed-export bypass (`esttab using "mytable.csv"`) is still rejected.
#
# Follow-up D fix: a left boundary `(?:^|[\\/])` is REQUIRED before the `tables/`/`figures/` segment.
# Without it, `.search` matched `tables/` as a SUBSTRING of a longer directory name (`mytables/`,
# `notes_tables/`, `vegetables/`, ...), wrongly clearing a "no canonical output folder" case (D1
# false negative) and disagreeing with the gate's quote-anchored inline regex. The boundary forces
# `tables`/`figures` to start at the path head or right after a separator.
_OUT_TABLE_PATH = re.compile(r'(?:^|[\\/])(?:[\w.\-]+[\\/])*tables[\\/]', re.IGNORECASE)
_OUT_FIGURE_PATH = re.compile(r'(?:^|[\\/])(?:[\w.\-]+[\\/])*figures[\\/]', re.IGNORECASE)


def _has_canonical_export(body: list[str], cmd_re: re.Pattern[str], out_re: re.Pattern[str]) -> bool:
    for ln in body:
        masked = _mask_r_strings_comments(ln)
        if cmd_re.search(masked) and out_re.search(ln):
            return True
    return False


def _toplevel_graph_line(text: str) -> int | None:
    brace_depth = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if brace_depth == 0 and _GRAPH_CMD.search(line):
            return i
        masked = _mask_r_strings_comments(line)
        brace_depth += masked.count("{") - masked.count("}")
        if brace_depth < 0:
            brace_depth = 0
    return None


def _section_spans(lines: list[str], header_re: re.Pattern[str]) -> list[tuple[str, int, int]]:
    starts = [(i, header_re.search(ln)) for i, ln in enumerate(lines)]
    headers = [(i, f"{m.group(1)} {m.group(2)}") for i, m in starts if m]
    spans = []
    for k, (i, label) in enumerate(headers):
        end = headers[k + 1][0] if k + 1 < len(headers) else len(lines)
        spans.append((label, i, end))
    return spans


def _detect_uncaptured_artifacts(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []

    table_spans = _section_spans(lines, _TABLE_HEADER)
    if table_spans:
        for label, start, end in table_spans:
            body = lines[start:end]
            has_est = any(_is_estimation(ln) for ln in body)
            has_exp = _has_canonical_export(body, _TABLE_EXPORT, _OUT_TABLE_PATH)
            if has_est and not has_exp:
                hits.append(_ev(path, start + 1, f"{label}: estimations build this table but no export saves it to output/tables/"))
    else:
        toplevel = _toplevel_estimation_lines(text)
        has_exp = _has_canonical_export(lines, _TABLE_EXPORT, _OUT_TABLE_PATH)
        if toplevel and not has_exp:
            hits.append(_ev(path, toplevel[0], "estimations build a table but no export saves coefficients to output/tables/"))

    figure_spans = _section_spans(lines, _FIGURE_HEADER)
    if figure_spans:
        for label, start, end in figure_spans:
            body = lines[start:end]
            has_graph = any(_GRAPH_CMD.search(ln) for ln in body)
            has_exp = _has_canonical_export(body, _GRAPH_EXPORT, _OUT_FIGURE_PATH)
            if has_graph and not has_exp:
                hits.append(_ev(path, start + 1, f"{label}: figure produced but no graph-export saves it to output/figures/"))
    else:
        gline = _toplevel_graph_line(text)
        has_exp = _has_canonical_export(lines, _GRAPH_EXPORT, _OUT_FIGURE_PATH)
        if gline is not None and not has_exp:
            hits.append(_ev(path, gline, "figure produced but no graph-export saves it to output/figures/"))
    return hits


def _detect_missing_table_comments(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    est_lines = _toplevel_estimation_lines(text)
    if len(est_lines) < 2:
        return []
    has_table_comment = any(_TABLE_HEADER.search(ln) or _FIGURE_HEADER.search(ln) for ln in lines)
    if has_table_comment:
        return []
    return [_ev(path, est_lines[0], f"{len(est_lines)} estimation commands, none anchored by a `* --> Table N` comment")]


def _detect_intermediate_data(root: Path, path: str, text: str, edges: list[Edge], texts: dict[str, str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = _DATA_WRITE.search(line)
        if not m:
            continue
        target = m.group(2).strip().replace("\\", "/")
        name = Path(target).name
        read_elsewhere = any(name in t for p, t in texts.items() if p != path)
        if not read_elsewhere:
            continue
        in_data_dir = "data/" in target.lower() or target.lower().startswith("data")
        if not in_data_dir:
            hits.append(_ev(path, i, f"writes intermediate '{name}' read by another script, but not under a canonical data/ folder"))
    return hits


def _detect_duplicate_readmes(root: Path) -> list[dict[str, Any]]:
    # group README-like files by (folder, stem): a same-name README.md + README.pdf is ONE document
    # in two formats (not flagged); distinct names or folders are separate drafts that can diverge.
    groups: dict[tuple[str, str], list[str]] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if "readme" in p.name.lower() and p.suffix.lower() in {".md", ".txt", ".pdf", ".rst"}:
            groups.setdefault((rel.parent.as_posix(), p.stem.lower()), []).append(rel.as_posix())
    if len(groups) <= 1:
        return []
    return [_ev(sorted(paths)[0]) for paths in groups.values()]


# D6: README references a path that isn't in the package. Conservative — only backtick-quoted path
# tokens in a markdown/text README (an author who writes `code/x.R` or `data/` in backticks means a
# real path). Folder-tree diagrams, prose, and PDF-extracted text never trigger it, so an illustrative
# tree root like `replication/` is not mistaken for a missing folder.
_README_PATHISH_EXT = (
    ".r", ".do", ".py", ".csv", ".dta", ".rds", ".rdata", ".xlsx", ".xls", ".sav",
    ".txt", ".tsv", ".parquet", ".ipynb", ".sql", ".rmd", ".qmd",
)
_README_BACKTICK = re.compile(r'`([^`\n]{1,80})`')


def _readme_pathish(tok: str) -> bool:
    tok = tok.strip()
    if not tok or " " in tok or "://" in tok:
        return False
    if tok.startswith(("http", "www.", "#", "@", "-", "$", "~")):
        return False
    if any(c in tok for c in "()=*<>|\"'{}!?,;"):
        return False
    return tok.endswith("/") or tok.lower().endswith(_README_PATHISH_EXT)


# README wording that documents a path as deliberately absent (restricted/not shipped). When it sits
# near a backtick path token, the token is a known omission, not a packaging mistake — do not flag it.
_ABSENT_WORDING = re.compile(
    r'not\s+(?:included|provided|shipped|available|public|distribut\w*|part\s+of)|'
    r'restrict\w*|confidential|propriet\w*|available\s+(?:up)?on\s+request|by\s+request|'
    r'cannot\s+be\s+(?:shared|included)|excluded|obtain\w*\s+(?:from|separately)',
    re.IGNORECASE,
)
_BRACE = re.compile(r'\{([^{}]*)\}')
_BRACE_RANGE = re.compile(r'^(\d+)\.\.(\d+)$')


def _expand_braces(tok: str) -> list[str]:
    """Expand a brace/ellipsis glob like `wave_{1,2,3}.dta` or `fig_{1..3}.pdf` into concrete names,
    so each member is checked against the package rather than the literal token being rejected."""
    m = _BRACE.search(tok)
    if not m:
        return [tok]
    opts: list[str] = []
    for opt in m.group(1).split(","):
        opt = opt.strip()
        rng = _BRACE_RANGE.match(opt)
        if rng and int(rng.group(1)) <= int(rng.group(2)) <= int(rng.group(1)) + 64:
            opts.extend(str(i) for i in range(int(rng.group(1)), int(rng.group(2)) + 1))
        else:
            opts.append(opt)
    prefix, suffix = tok[:m.start()], tok[m.end():]
    out: list[str] = []
    for p in opts:
        out.extend(_expand_braces(prefix + p + suffix))
    return out


def _detect_readme_missing_paths(root: Path) -> list[dict[str, Any]]:
    readme = None
    try:
        for p in root.iterdir():
            if p.is_file() and p.name.lower() in {"readme.md", "readme.txt"}:
                readme = p
                break
    except OSError:
        return []
    if readme is None:
        return []
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    rels: set[str] = set()
    names: set[str] = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        rels.add(rel.as_posix().lower())
        names.add(p.name.lower())

    def resolves(tok: str) -> bool:
        rel = tok.strip().strip("`").lstrip("./").rstrip("/").lower()
        return not rel or rel in rels or Path(rel).name in names

    root_token = root.name.lower()
    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    for m in _README_BACKTICK.finditer(text):
        tok = m.group(1).strip()
        if tok in seen:
            continue
        seen.add(tok)
        if tok.lower().rstrip("/") == root_token:
            continue  # the package's own root folder, not a missing sub-path
        if _ABSENT_WORDING.search(text[max(0, m.start() - 200): m.start() + 200]):
            continue  # documented as deliberately not shipped
        candidates = _expand_braces(tok) if ("{" in tok and "}" in tok) else [tok]
        for cand in candidates:
            if _readme_pathish(cand) and not resolves(cand):
                hits.append(_ev(readme.name, None, f"README references `{tok}` but it is not in the package"))
                break
    return hits[:8]


# A13: a code file that nothing runs, once a master/sourcing structure is present.
def _detect_unreferenced_scripts(entries: list[FileEntry], edges: list[Edge], texts: dict[str, str]) -> list[dict[str, Any]]:
    callers = {e.src for e in edges if e.kind in {"do", "source"}}
    if not callers:  # no run structure at all -> A1/A11 own that case, not this rule
        return []
    referenced = {e.dst for e in edges if e.kind in {"do", "source"} and e.resolved}
    hits: list[dict[str, Any]] = []
    for path in sorted(p for p in texts):
        if path in referenced or path in callers:
            continue
        base = Path(path).name
        # a helper sourced via a path the graph could not resolve still has its name typed elsewhere
        if any(base in other for q, other in texts.items() if q != path):
            continue
        hits.append(_ev(path))
    return hits[:8]


# N5: a filename a shell or another tool will choke on.
_UNSAFE_FILENAME = re.compile(r"""[ &;|()$`'"*?<>]""")


def _detect_unsafe_filenames(root: Path, entries: list[FileEntry]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for e in entries:
        if e.language in {"stata", "r", "python", "data"}:
            name = Path(e.path).name
            if _UNSAFE_FILENAME.search(name):
                hits.append(_ev(e.path, None, "filename has a space or a shell-unsafe character"))
    return hits[:8]


# A5 / A14 / A15: missing-input detection over the dependency graph, confidence-gated.
#   A5  (P0): an unresolved INCLUDE target (do/source/import literal that resolves to no file).
#   A14 (P0): an unresolved RELATIVE data READ literal, absent and produced by NO write edge.
#   A15 (P2): a basename-collision (ambiguous) include/read — never a P0, surfaced as advisory.
# A target produced by a write edge is a pipeline intermediate, not a missing input (D3 owns it). An
# absolute-path read is B4's domain. A dynamic path (no literal) never reaches here — it has no edge.
def _missing_inputs(edges: list[Edge], lang_of) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    write_basenames = {Path(e.dst).name.lower() for e in edges if e.kind == "write"}
    a5: list[dict[str, Any]] = []
    a14: list[dict[str, Any]] = []
    a15: list[dict[str, Any]] = []
    for e in edges:
        base = Path(e.dst).name
        if e.status == "ambiguous":
            if e.kind in _INCLUDE_KINDS or e.kind in _READ_KINDS:
                a15.append(_ev(e.src, None, f"references '{base}' but the package ships more than one file with that name"))
            continue
        if e.status != "unresolved":
            continue
        if base.lower() in write_basenames:
            continue  # produced elsewhere by a write edge -> intermediate, not a missing input
        if e.kind in _INCLUDE_KINDS:
            a5.append(_ev(e.src, None, f"includes '{e.dst}' but no such file ships in the package"))
        elif e.kind in _READ_KINDS:
            if _ABS_TARGET.match(e.dst):
                continue  # absolute path -> B4 owns it; do not double-flag
            if lang_of(e.src) not in {"stata", "r"}:
                continue  # Python/Julia best-effort only -> never P0
            a14.append(_ev(e.src, None, f"reads '{e.dst}' but no such file ships and no script writes it"))
    return a5, a14, a15


def run(root: Path, entries: list[FileEntry], edges: list[Edge], table_exports) -> list[Finding]:
    root = root.resolve()
    rules = {r["id"]: r for r in load_rules()}
    texts = _texts(root, entries)
    stems = _shipped_stems(root)
    findings: list[Finding] = []

    def emit(rule_id: str, evidence: list[dict[str, Any]], rationale: str) -> None:
        if not evidence:
            return
        r = rules[rule_id]
        findings.append(
            Finding(
                rule_id=rule_id,
                category=r["category"],
                kind=r["kind"],
                priority=r["priority"],
                message=r["rule"],
                evidence=evidence,
                rationale=rationale,
                source_lessons=r.get("source_lessons", []),
                why_downstream=r.get("why_downstream", ""),
                target_form=r.get("target_form", ""),
                lossless_note=r.get("lossless_note", ""),
                propose_only=bool(r.get("propose_only", False)),
                output_changing=bool(r.get("output_changing", False)),
            )
        )

    callers = {e.src for e in edges if e.kind in {"do", "source"}}
    script_paths = [e.path for e in entries if e.language in {"stata", "r", "python"}]
    if not callers and len(script_paths) > 1:
        emit("A1-master-entry", [_ev(p) for p in sorted(texts)][:1],
             "No script sources/does any other; build order is implicit.")
        readme_has_order = any(
            re.search(r'(run|execut|order|step\s*\d|^\s*\d+[.)]\s)', (root / e.path).read_text(encoding="utf-8", errors="replace"), re.IGNORECASE | re.MULTILINE)
            for e in entries if e.language == "doc" and e.path.lower().endswith((".md", ".txt"))
        )
        if not readme_has_order:
            emit("A11-explicit-run-order", [_ev(p) for p in sorted(script_paths)][:1],
                 f"{len(script_paths)} analysis scripts, no master script and no README run-order.")

    doc_files = [e.path for e in entries if e.language == "doc" and e.path.lower().endswith((".md", ".txt"))]
    data_files = [e.path for e in entries if e.language == "data"]
    n_files = len(script_paths) + len(data_files)
    if n_files > 1:
        documented = set()
        for d in doc_files:
            dtext = (root / d).read_text(encoding="utf-8", errors="replace")
            for fp in script_paths + data_files:
                if Path(fp).name in dtext:
                    documented.add(fp)
        undocumented = [fp for fp in script_paths + data_files if fp not in documented]
        if undocumented:
            detail = "no README" if not doc_files else f"{len(undocumented)} of {n_files} files not described in any README"
            emit("D4-per-file-documentation", [_ev(p) for p in sorted(undocumented)][:8],
                 f"{detail}; per-file documentation (purpose, inputs/outputs, codebook) missing.")

    emit("D5-duplicate-readme", _detect_duplicate_readmes(root),
         "Multiple distinct README documents (different names or folders) that can diverge and mislead a replicator.")

    emit("D6-readme-missing-paths", _detect_readme_missing_paths(root),
         "README references files or folders that are not present in the package.")

    emit("A13-unreferenced-script", _detect_unreferenced_scripts(entries, edges, texts),
         "A code file is never run by the master or any other script and is not named anywhere else.")

    emit("N5-unsafe-filename", _detect_unsafe_filenames(root, entries),
         "A script or data filename contains a space or a character that breaks shells and tools.")

    a5_ev, a14_ev, a15_ev = _missing_inputs(edges, lambda p: _lang_of(entries, p))
    emit("A5-stable-includes", a5_ev,
         "A do/source/import target does not resolve to any file shipped in the package.")
    emit("A14-missing-input", a14_ev,
         "A relative data read points at a file that is absent and that no script in the package writes.")
    emit("A15-ambiguous-input-path", a15_ev,
         "An include/read names a file by a basename that more than one shipped file matches, so which one loads depends on the working directory.")

    emit("D7-codebook-coverage", _detect_codebook_coverage(root, entries, texts),
         "A shipped codebook exists but some variables used in estimation commands are not documented in it.")

    for path, text in texts.items():
        lang = _lang_of(entries, path)

        for line_no, line in _code_line_hits(text, _ABS_PATH, lang):
            emit("B4-no-abs-paths", [_ev(path, line_no, line)], "Absolute path literal found.")

        if lang in {"stata", "r"}:
            emit("A12-table-comment-mapping", _detect_missing_table_comments(path, text),
                 "Multiple estimations with no `-> Table N` comments anchoring the table<->command mapping.")
            emit("D1-output-artifact-coverage", _detect_uncaptured_artifacts(path, text),
                 "Estimation/figure present but no export saves the artifact to a relative output/ folder.")
            emit("D3-intermediate-data-hygiene", _detect_intermediate_data(root, path, text, edges, texts),
                 "Intermediate dataset written outside a canonical data/ folder is read by another script.")
            emit("C8-unseeded-stochastic", _detect_unseeded_stochastic(path, text, lang),
                 "Stochastic operation with no seed; a re-run draws different numbers than the paper reports.")

        if lang in {"stata", "r"}:
            loop_depth = 0
            for line_no, line in enumerate(text.splitlines(), start=1):
                code = _strip_comment_keep_strings(line, lang)
                if _LOOP_HEAD.search(code):
                    loop_depth += 1
                if loop_depth > 0 and _EXPORT_FIXED.search(code):
                    emit("B1-minimize-loops", [_ev(path, line_no, line)],
                         "Fixed-filename table export inside a loop overwrites per iteration.")
                if loop_depth > 0 and _is_estimation(code):
                    emit("N2-explicit-table-commands", [_ev(path, line_no, line)],
                         "Estimation inside a loop hides the model->table-cell mapping from the pipeline.")
                if re.match(r'^\s*\}', code) and loop_depth > 0:
                    loop_depth -= 1

        if lang == "stata":
            if _ESTIMATION.search(text) and not _DATA_LOAD_STATA.search(text):
                if not _upstream_loads_data(path, edges, texts, _DATA_LOAD_STATA):
                    emit("A3-data-load", [_ev(path)],
                         "Estimation present but no use/import in this script, and no upstream script loads data first.")
            ts_hits = _code_line_hits(text, _TS_OP, lang)
            if ts_hits and not _TSSET.search(text):
                emit("A4-panel-declare", [_ev(path, ts_hits[0][0], ts_hits[0][1])],
                     "Time-series operators without a prior tsset/xtset.")
            for line_no, line in _code_line_hits(text, _CLEAR_ALL, lang):
                if path not in callers:
                    emit("B7-no-cross-script-clearall", [_ev(path, line_no, line)],
                         "clear all in a non-master script drops programs later scripts need.")
            for line_no, line in _code_line_hits(text, _WIDE_WILDCARD, lang):
                emit("B3-no-wide-wildcard", [_ev(path, line_no, line)],
                     "Wildcard varlist may expand past 20 columns.")
            if _VERSION_SENSITIVE.search(text) and not _VERSION_STMT.search(text):
                emit("C3-declare-stata-version", [_ev(path)],
                     "Version-sensitive command without a `version NN` declaration.")
            emit("A6-guarded-fallback-load", _detect_guarded_fallback(root, path, text),
                 "Guarded `capture use A` + `if _rc!=0 {use B}`; A ships so the fallback to B never runs.")
            emit("A7-var-lifecycle-contradiction", _detect_lifecycle_contradiction(path, text),
                 "Variable used after it was dropped or renamed away.")
            emit("A8-data-ref-extension-mismatch", _detect_data_ref_mismatch(root, path, text, stems),
                 "Data reference does not resolve, but a same-stem file with a different extension ships.")
            emit("A9-nested-cd", _detect_relative_cd(path, text),
                 "Relative `cd` mid-script breaks relative paths when run from the package root.")
            emit("C4-deprecated-syntax-signature", _detect_compat_signatures(path, text, bool(_VERSION_STMT.search(text))),
                 "Version-fragile command syntax without a declared version.")
            emit("B10-embedded-foreign-code", _detect_embedded_foreign(path, text),
                 "Non-Stata (R-style) code in a .do file halts Stata before regressions.")
            for line_no, line in _code_line_hits(text, _QUIET_LOAD, lang):
                emit("B9-suppressed-data-load", [_ev(path, line_no, line)],
                     "quietly around use/import hides a missing-file failure.")
            emit("N1-no-delimit-semicolon", _detect_delimit(path, text),
                 "#delimit ; changes the statement terminator for a whole region; `///` is line-local and unambiguous.")
            emit("N4-named-estimation-calls", _detect_wrapper_estimation(path, text),
                 "Estimation inside a user program slips past output capture and is harder to read; call estimators directly.")
            emit("C2-vendor-ado", _detect_unvendored_ado(root, path, text),
                 "User-written ado command used but not shipped and not ssc-installed.")
            emit("C6-old-stata-merge-syntax", _detect_old_merge(path, text),
                 "Pre-Stata-11 `merge varlist using` syntax fails on modern Stata; use `merge m:1`/`1:1`.")
            emit("A10-commented-restricted-regression", _detect_commented_restricted(path, text),
                 "Commented-out regression with nearby restricted-data wording.")

        if lang == "r":
            if _has_toplevel_estimation(text) and not _DATA_LOAD_R.search(text):
                if not _upstream_loads_data(path, edges, texts, _DATA_LOAD_R):
                    emit("A3-data-load", [_ev(path)],
                         "Estimation present but no read/load in this script, and no upstream script loads data first.")
            for line_no, line in _code_line_hits(text, _GITHUB_INSTALL, lang):
                emit("C1-pin-deps", [_ev(path, line_no, line)], "Unpinned direct-from-source install.")
            emit("C5-deprecated-r-packages", _detect_deprecated_r_pkg(path, text),
                 "Removed/deprecated R package loaded at top halts the whole script.")
            emit("C7-nonreproducible-parallel-rng", _detect_nonreproducible_parallel_rng(path, text),
                 "Parallel %dopar% loop without doRNG/registerDoRNG draws a different RNG stream each run.")
            emit("B11-rmd-chunk-in-r", _detect_rmd_chunk(path, text),
                 "R Markdown ```{r} chunk markers in a .R file cause a parse error.")
            emit("B8-r-table-call-syntax", _detect_r_table_syntax(path, text),
                 "stargazer/xtable call has unbalanced delimiters across its span.")
            emit("N3-compact-r-table-calls", _detect_long_r_table_call(path, text),
                 "A sprawling multi-line table call is fragile to comment-cleaning and hard to read.")
            emit("A10-commented-restricted-regression", _detect_commented_restricted(path, text),
                 "Commented-out regression with nearby restricted-data wording.")

    return _dedupe(findings)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    merged: dict[str, Finding] = {}
    for f in findings:
        if f.rule_id not in merged:
            merged[f.rule_id] = f
        else:
            merged[f.rule_id].evidence.extend(f.evidence)
    return list(merged.values())
