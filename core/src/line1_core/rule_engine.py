from __future__ import annotations

from typing import Any

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .dependency_graph import Edge
from .inventory import FileEntry

_RULES_FILE = Path(__file__).parent / "rules" / "author_rules.yaml"

_ABS_PATH = re.compile(r'["\']?((?:[A-Za-z]:\\|\\\\|/Users/|/home/|~/)[^"\'\r\n]+)["\']?')
_LOOP_HEAD = re.compile(r'^\s*(foreach|forvalues|forv|while|for)\b', re.IGNORECASE)
_EXPORT_FIXED = re.compile(r'\b(esttab|estout|outreg2?|putexcel|tabout)\b[^\r\n]*using\s+["\']?([^\s"\'`,]+)', re.IGNORECASE)
_TS_OP = re.compile(r'(?<![\w.])([LDF]\d*\.\w+)')
_TSSET = re.compile(r'^\s*(tsset|xtset)\b', re.IGNORECASE | re.MULTILINE)
# Allow common Stata prefixes before the estimator: `xi:`, `by/bysort ... :`, `quietly`,
# `capture`, `noisily`, `svy:` — otherwise `xi: reg ...` / `bysort y: reg ...` are missed.
_STATA_PREFIX = r'(?:(?:cap(?:ture)?|qui(?:etly)?|noi(?:sily)?|xi|svy|by(?:sort)?\s+[^\r\n:]+)[\s:]+)*'
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
_GRAPH_CMD = re.compile(r'^\s*(graph\s+(?:twoway|bar|box|matrix|combine|tw)|twoway|histogram|scatter|kdensity|coefplot|marginsplot|ggplot|plot\()', re.IGNORECASE)
_GRAPH_EXPORT = re.compile(r'\b(graph\s+export|graph\s+save|ggsave|gr\s+export|dev\.copy|pdf\(|png\(|postscript\()', re.IGNORECASE)
# D3 intermediate data write / read
_DATA_WRITE = re.compile(r'^\s*(?:cap(?:ture)?\s+|qui(?:etly)?\s+)*(save|saveold|export\s+delimited|outsheet|saveRDS|write[._]csv|write[._]dta|write[._]rds|haven::write_dta|saveRDS)\b[^\r\n]*?["\']?([\w./\\-]+\.(?:dta|csv|rds|rdata|tab|parquet))["\']?', re.IGNORECASE)
_FILE_EXISTS_GUARD = re.compile(r'(confirm\s+file|file\.exists|os\.path\.exists|assert\s+_rc|fileexists)', re.IGNORECASE)
# D1 table/figure section headers in comments (e.g. "* Table 3: ..." / "# Figure 2")
_TABLE_HEADER = re.compile(r'^\s*(?:\*+|//+|#+)\s*\**\s*(Table|Tabla)\s+([A-Za-z]?\.?\d+)\b', re.IGNORECASE)
_FIGURE_HEADER = re.compile(r'^\s*(?:\*+|//+|#+)\s*\**\s*(Figure|Fig\.?|Figura)\s+([A-Za-z]?\.?\d+)\b', re.IGNORECASE)


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


def _line_hits(text: str, regex: re.Pattern[str]) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
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
    hits: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _REGHDFE_IV.search(line):
            hits.append(_ev(path, i, f"reghdfe IV-syntax (use ivreghdfe or pin version): {line.strip()[:90]}"))
        elif _RDROBUST_DEPR.search(line):
            hits.append(_ev(path, i, f"rdrobust deprecated bwselect(): {line.strip()[:90]}"))
        elif _TABLE_C.match(line):
            hits.append(_ev(path, i, f"`table var, c(...)` removed in Stata 17: {line.strip()[:90]}"))
        elif _TMPDIR.search(line) and not has_version:
            hits.append(_ev(path, i, f"tmpdir needs Stata 17+; declare version: {line.strip()[:90]}"))
        elif _LEGACY_MIXED.match(line):
            hits.append(_ev(path, i, f"legacy mixed-model command (hangs/removed on modern Stata; use me-prefix): {line.strip()[:90]}"))
        elif _CD_EMPTY.match(line):
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
            has_exp = any(_TABLE_EXPORT.search(_mask_r_strings_comments(ln)) for ln in body)
            if has_est and not has_exp:
                hits.append(_ev(path, start + 1, f"{label}: estimations build this table but no export saves it to output/tables/"))
    else:
        toplevel = _toplevel_estimation_lines(text)
        has_exp = any(_TABLE_EXPORT.search(_mask_r_strings_comments(ln)) for ln in lines)
        if toplevel and not has_exp:
            hits.append(_ev(path, toplevel[0], "estimations build a table but no export saves coefficients to output/tables/"))

    figure_spans = _section_spans(lines, _FIGURE_HEADER)
    if figure_spans:
        for label, start, end in figure_spans:
            body = lines[start:end]
            has_graph = any(_GRAPH_CMD.search(ln) for ln in body)
            has_exp = any(_GRAPH_EXPORT.search(ln) for ln in body)
            if has_graph and not has_exp:
                hits.append(_ev(path, start + 1, f"{label}: figure produced but no graph-export saves it to output/figures/"))
    else:
        gline = _toplevel_graph_line(text)
        has_exp = any(_GRAPH_EXPORT.search(ln) for ln in lines)
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

    for path, text in texts.items():
        lang = _lang_of(entries, path)

        for line_no, line in _line_hits(text, _ABS_PATH):
            emit("B4-no-abs-paths", [_ev(path, line_no, line)], "Absolute path literal found.")

        if lang in {"stata", "r"}:
            emit("A12-table-comment-mapping", _detect_missing_table_comments(path, text),
                 "Multiple estimations with no `-> Table N` comments anchoring the table<->command mapping.")
            emit("D1-output-artifact-coverage", _detect_uncaptured_artifacts(path, text),
                 "Estimation/figure present but no export saves the artifact to a relative output/ folder.")
            emit("D3-intermediate-data-hygiene", _detect_intermediate_data(root, path, text, edges, texts),
                 "Intermediate dataset written outside a canonical data/ folder is read by another script.")

        if lang in {"stata", "r"}:
            loop_depth = 0
            for line_no, line in enumerate(text.splitlines(), start=1):
                if _LOOP_HEAD.search(line):
                    loop_depth += 1
                if loop_depth > 0 and _EXPORT_FIXED.search(line):
                    emit("B1-minimize-loops", [_ev(path, line_no, line)],
                         "Fixed-filename table export inside a loop overwrites per iteration.")
                if loop_depth > 0 and _is_estimation(line):
                    emit("N2-explicit-table-commands", [_ev(path, line_no, line)],
                         "Estimation inside a loop hides the model->table-cell mapping from the pipeline.")
                if re.match(r'^\s*\}', line) and loop_depth > 0:
                    loop_depth -= 1

        if lang == "stata":
            if _ESTIMATION.search(text) and not _DATA_LOAD_STATA.search(text):
                if not _upstream_loads_data(path, edges, texts, _DATA_LOAD_STATA):
                    emit("A3-data-load", [_ev(path)],
                         "Estimation present but no use/import in this script, and no upstream script loads data first.")
            ts_hits = _line_hits(text, _TS_OP)
            if ts_hits and not _TSSET.search(text):
                emit("A4-panel-declare", [_ev(path, ts_hits[0][0], ts_hits[0][1])],
                     "Time-series operators without a prior tsset/xtset.")
            for line_no, line in _line_hits(text, _CLEAR_ALL):
                if path not in callers:
                    emit("B7-no-cross-script-clearall", [_ev(path, line_no, line)],
                         "clear all in a non-master script drops programs later scripts need.")
            for line_no, line in _line_hits(text, _WIDE_WILDCARD):
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
            for line_no, line in _line_hits(text, _QUIET_LOAD):
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
            for line_no, line in _line_hits(text, _GITHUB_INSTALL):
                emit("C1-pin-deps", [_ev(path, line_no, line)], "Unpinned direct-from-source install.")
            emit("C5-deprecated-r-packages", _detect_deprecated_r_pkg(path, text),
                 "Removed/deprecated R package loaded at top halts the whole script.")
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
