from __future__ import annotations

from typing import Any

import re
from dataclasses import dataclass
from pathlib import Path

from .inventory import FileEntry

# --- Edge taxonomy -----------------------------------------------------------------------------
# kind is the specific verb class; status is the 3-tier resolution confidence. The edge CLASS
# (include / read / write) is derived from kind via the sets below — A5/A14 and the orphan
# detector key off the class, not the raw kind.
_INCLUDE_KINDS = frozenset({"do", "source", "import"})
_READ_KINDS = frozenset({"data_use", "read"})
_WRITE_KINDS = frozenset({"write"})


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str          # do | source | import | data_use | read | write
    status: str        # resolved | unresolved | ambiguous

    @property
    def resolved(self) -> bool:
        # back-compat: every existing consumer reads `.resolved` as a bool. A basename collision
        # (ambiguous) is deliberately NOT resolved — never silently pick the first hit.
        return self.status == "resolved"

    @property
    def edge_class(self) -> str:
        if self.kind in _INCLUDE_KINDS:
            return "include"
        if self.kind in _WRITE_KINDS:
            return "write"
        return "read"


# --- Stata: line-level patterns (do/run includes, use/import reads, save/export/graph writes) ---
_STATA_PRE = r'(?:cap(?:ture)?\s+|qui(?:etly)?\s+|noi(?:sily)?\s+)*'
_STATA_DO = re.compile(r'^\s*' + _STATA_PRE + r'(?:do|run)\s+"?([^"\r\n,]+?\.do)"?', re.IGNORECASE | re.MULTILINE)
_STATA_USE = re.compile(r'^\s*' + _STATA_PRE + r'use\s+"?([^"\r\n,]+?\.dta)"?', re.IGNORECASE | re.MULTILINE)
_STATA_READ = re.compile(
    r'^\s*' + _STATA_PRE + r'(?:import\s+delimited|import\s+excel|insheet|infile)\b'
    r'[^\r\n]*?"?([\w./\\$ -]+?\.(?:csv|tab|txt|xlsx|xls|dat|dta))"?',
    re.IGNORECASE | re.MULTILINE,
)
_STATA_WRITE = re.compile(
    r'^\s*' + _STATA_PRE + r'(?:save|saveold|export\s+delimited|export\s+excel|outsheet|'
    r'graph\s+export|graph\s+save|esttab|estout|outreg2?|putexcel|putdocx|tabout)\b'
    r'[^\r\n]*?"?([\w./\\$ -]+?\.(?:dta|csv|tab|txt|xlsx|xls|parquet|pdf|png|eps|ps|svg|gph|tex|rtf|doc|docx))"?',
    re.IGNORECASE | re.MULTILINE,
)

# --- R / Python: call-based extraction (the keystone fix) --------------------------------------
# Old engine matched only `source("literal")` — a `source(file.path(CODE,"x.R"))` slipped past. We
# now find the verb, walk its balanced parens, and pick the path-shaped string literal inside, so
# file.path()/paste0()/here()/glue() wrappers resolve via their literal segment.
_INCLUDE_VERBS = ("source", "sys.source")
_READ_VERBS = (
    "read.csv", "read.csv2", "read.delim", "read.delim2", "read.table", "read_csv", "read_csv2",
    "read_tsv", "read_delim", "read_table", "read_dta", "read.dta", "read.dta13", "read_stata",
    "readRDS", "read_rds", "load", "fread", "st_read", "read_excel", "read_xlsx", "read_sav",
    "read_spss", "read_parquet", "read_feather", "read_pickle", "read_json",
)
_WRITE_VERBS = (
    "write.csv", "write.csv2", "write.table", "write_csv", "write_tsv", "write_delim", "fwrite",
    "saveRDS", "save", "write_rds", "write_dta", "write.dta", "write.dta13", "write_xlsx",
    "st_write", "ggsave", "pdf", "png", "jpeg", "tiff", "bmp", "svg", "postscript", "cairo_pdf",
    "dev.copy2pdf", "stargazer", "etable", "texreg", "htmlreg", "modelsummary",
    "to_csv", "to_stata", "to_parquet", "to_excel", "to_pickle", "savefig",
)
_VERB_CLASS: dict[str, str] = {}
for _v in _INCLUDE_VERBS:
    _VERB_CLASS[_v] = "include"
for _v in _READ_VERBS:
    _VERB_CLASS[_v] = "read"
for _v in _WRITE_VERBS:
    _VERB_CLASS[_v] = "write"
# longest-first so `read.csv2` wins over `read.csv`; lookbehind blocks `myread_csv`, allows `pd.read_csv`.
_VERB_RE = re.compile(
    r'(?<![\w])(' + '|'.join(re.escape(v) for v in sorted(_VERB_CLASS, key=len, reverse=True)) + r')\s*\('
)
_KIND_BY_CLASS = {"include": "source", "read": "read", "write": "write"}

_CODE_EXT = (".r", ".do", ".py")
_DATA_EXT = (
    ".csv", ".dta", ".rds", ".rdata", ".tab", ".parquet", ".xlsx", ".xls", ".sav",
    ".tsv", ".dat", ".txt", ".feather", ".json", ".pkl",
)
_GRAPHIC_EXT = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps", ".svg", ".tex", ".html", ".tiff", ".bmp", ".gph")
_EXT_BY_CLASS = {"include": _CODE_EXT, "read": _DATA_EXT, "write": _DATA_EXT + _GRAPHIC_EXT}

_STR_LIT = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
_PY_IMPORT_LOCAL = re.compile(r'^\s*(?:from|import)\s+([A-Za-z_][\w.]*)', re.MULTILINE)


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _strip_line_comments(text: str) -> str:
    """Blank trailing `#` comments per physical line while preserving string literals, so the verb
    scan never trips on a verb name written inside a comment, but still sees real path literals."""
    out: list[str] = []
    for line in text.splitlines():
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch in '"\'':
                m = _STR_LIT.match(line, i)
                if m:
                    i = m.end()
                    continue
                i += 1
                continue
            if ch == '#':
                line = line[:i]
                break
            i += 1
        out.append(line)
    return "\n".join(out)


def _resolve(root: Path, from_rel: str, target: str) -> tuple[str, str]:
    """Return (dst, status) where status is resolved | unresolved | ambiguous. Deterministic:
    candidates are sorted, and a basename collision with no exact path match is `ambiguous` — we
    never silently return the first rglob hit."""
    target_clean = target.strip().replace("\\", "/")
    if target_clean.startswith("./"):
        target_clean = target_clean[2:]
    if not target_clean:
        return target.strip(), "unresolved"
    base = Path(target_clean).name
    caller_dir = (root / from_rel).parent
    for cand in ((root / target_clean), (caller_dir / target_clean)):
        if cand.is_file():
            try:
                return str(cand.resolve().relative_to(root)), "resolved"
            except ValueError:
                pass
    hits = sorted(str(p.relative_to(root)) for p in root.rglob(base) if p.is_file())
    if not hits:
        return target_clean, "unresolved"
    if len(hits) == 1:
        return hits[0], "resolved"
    return target_clean, "ambiguous"


def _call_literals(text: str, open_paren: int) -> list[str]:
    """String literals inside the balanced parens of a call whose `(` is at index open_paren."""
    depth = 0
    i = open_paren
    n = len(text)
    lits: list[str] = []
    while i < n:
        ch = text[i]
        if ch in '"\'':
            m = _STR_LIT.match(text, i)
            if m:
                lits.append(m.group(0)[1:-1])
                i = m.end()
                continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    return lits


def _pick_filename(lits: list[str], exts: tuple[str, ...]) -> str | None:
    """The last string literal whose basename ends with an expected extension (the filename is
    usually the last path segment, e.g. file.path(dir, "x.R"))."""
    chosen = None
    for lit in lits:
        name = Path(lit.strip().replace("\\", "/")).name.lower()
        if name.endswith(exts):
            chosen = lit
    return chosen


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _call_edges(root: Path, rel: str, text: str) -> list[Edge]:
    clean = _strip_line_comments(text)
    edges: list[Edge] = []
    for m in _VERB_RE.finditer(clean):
        verb = m.group(1)
        klass = _VERB_CLASS[verb]
        lits = _call_literals(clean, m.end() - 1)
        target = _pick_filename(lits, _EXT_BY_CLASS[klass])
        if target is None:
            continue
        dst, status = _resolve(root, rel, target)
        edges.append(Edge(src=rel, dst=dst, kind=_KIND_BY_CLASS[klass], status=status))
    return edges


def _py_import_edges(root: Path, rel: str, text: str) -> list[Edge]:
    """Python local-module imports only: emit an edge ONLY when the imported name resolves to a
    sibling .py in the package. Library imports (numpy, pandas) never become unresolved includes."""
    edges: list[Edge] = []
    seen: set[str] = set()
    for m in _PY_IMPORT_LOCAL.finditer(text):
        mod = m.group(1).split(".")[0]
        if mod in seen:
            continue
        seen.add(mod)
        dst, status = _resolve(root, rel, mod + ".py")
        if status == "resolved":
            edges.append(Edge(src=rel, dst=dst, kind="import", status=status))
    return edges


def _stata_edges(root: Path, rel: str, text: str) -> list[Edge]:
    edges: list[Edge] = []
    specs = [(_STATA_DO, "do"), (_STATA_USE, "data_use"), (_STATA_READ, "data_use"), (_STATA_WRITE, "write")]
    for regex, kind in specs:
        for match in regex.finditer(text):
            dst, status = _resolve(root, rel, match.group(1))
            edges.append(Edge(src=rel, dst=dst, kind=kind, status=status))
    return edges


def build(root: Path, entries: list[FileEntry]) -> list[Edge]:
    root = root.resolve()
    edges: list[Edge] = []
    for entry in entries:
        if entry.language not in {"stata", "r", "python"}:
            continue
        text = _read_text(root, entry.path)
        if entry.language == "stata":
            edges.extend(_stata_edges(root, entry.path, text))
        else:
            edges.extend(_call_edges(root, entry.path, text))
            if entry.language == "python":
                edges.extend(_py_import_edges(root, entry.path, text))
    return edges


def entry_points(entries: list[FileEntry], edges: list[Edge]) -> list[dict[str, Any]]:
    code = {e.path for e in entries if e.language in {"stata", "r", "python"}}
    callers = {e.src for e in edges if e.kind in _INCLUDE_KINDS}
    called = {e.dst for e in edges if e.kind in _INCLUDE_KINDS and e.resolved}
    points: list[dict[str, Any]] = []
    for path in sorted(callers - called):
        points.append({"path": path, "reason": "runs other scripts but is not run by any"})
    if not callers:
        for path in sorted(code):
            name = Path(path).name.lower()
            if any(token in name for token in ("master", "main", "run_all", "runall", "00_", "_00")):
                points.append({"path": path, "reason": "name suggests a master/entry script"})
    return points
