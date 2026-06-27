"""Phase 1 graph substrate: balanced-paren literal extraction, 3-tier resolution, typed I/O edges.

The NEGATIVE cases (a comment is not an edge, a library import is not a missing include, a fully
dynamic path makes no edge) are the real deliverable — they are what catch the next false positive.
"""
from __future__ import annotations

from pathlib import Path

from line1_core import dependency_graph, inventory


def _edges(root: Path) -> list[dependency_graph.Edge]:
    return dependency_graph.build(root, inventory.scan(root))


def _find(edges: list[dependency_graph.Edge], *, kind: str | None = None, dst_ends: str | None = None):
    out = []
    for e in edges:
        if kind is not None and e.kind != kind:
            continue
        if dst_ends is not None and not e.dst.endswith(dst_ends):
            continue
        out.append(e)
    return out


# --- the keystone: wrappers around the literal now resolve ------------------------------------

def test_filepath_wrapped_source_resolves(tmp_path: Path) -> None:
    pkg = tmp_path / "fp"
    (pkg / "code").mkdir(parents=True)
    (pkg / "master.R").write_text('source(file.path("code", "helper.R"))\n', encoding="utf-8")
    (pkg / "code" / "helper.R").write_text("f <- function() 1\n", encoding="utf-8")
    inc = _find(_edges(pkg), kind="source", dst_ends="helper.R")
    assert inc and inc[0].status == "resolved", inc


def test_paste0_wrapped_read_resolves(tmp_path: Path) -> None:
    pkg = tmp_path / "p0"
    (pkg / "data").mkdir(parents=True)
    (pkg / "a.R").write_text('df <- read_csv(paste0(data_dir, "raw.csv"))\n', encoding="utf-8")
    (pkg / "data" / "raw.csv").write_text("x\n1\n", encoding="utf-8")
    rd = _find(_edges(pkg), kind="read", dst_ends="raw.csv")
    assert rd and rd[0].status == "resolved", rd


# --- 3-tier resolution: resolved / unresolved / ambiguous -------------------------------------

def test_basename_collision_is_ambiguous(tmp_path: Path) -> None:
    pkg = tmp_path / "amb"
    (pkg / "data").mkdir(parents=True)
    (pkg / "other").mkdir(parents=True)
    (pkg / "data" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "other" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "a.R").write_text('d <- read.csv("x.csv")\n', encoding="utf-8")
    rd = _find(_edges(pkg), kind="read", dst_ends="x.csv")
    assert rd and rd[0].status == "ambiguous", rd
    assert rd[0].resolved is False  # an ambiguous edge is NEVER reported resolved


def test_exact_path_beats_collision(tmp_path: Path) -> None:
    pkg = tmp_path / "exact"
    (pkg / "data").mkdir(parents=True)
    (pkg / "other").mkdir(parents=True)
    (pkg / "data" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "other" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "a.R").write_text('d <- read.csv("data/x.csv")\n', encoding="utf-8")
    rd = _find(_edges(pkg), kind="read", dst_ends="x.csv")
    assert rd and rd[0].status == "resolved" and rd[0].dst == "data/x.csv", rd


def test_missing_literal_is_unresolved(tmp_path: Path) -> None:
    pkg = tmp_path / "miss"
    pkg.mkdir()
    (pkg / "a.R").write_text('d <- read.csv("nope.csv")\n', encoding="utf-8")
    rd = _find(_edges(pkg), kind="read", dst_ends="nope.csv")
    assert rd and rd[0].status == "unresolved", rd


# --- typed write edges -------------------------------------------------------------------------

def test_write_edges_emitted(tmp_path: Path) -> None:
    pkg = tmp_path / "w"
    pkg.mkdir()
    (pkg / "a.R").write_text(
        'ggsave("output/figures/f.pdf", p)\n'
        'write.csv(df, "output/tables/t.csv")\n'
        'saveRDS(obj, file = "data/cache.rds")\n',
        encoding="utf-8",
    )
    edges = _edges(pkg)
    assert _find(edges, kind="write", dst_ends="f.pdf"), edges
    assert _find(edges, kind="write", dst_ends="t.csv"), edges
    assert _find(edges, kind="write", dst_ends="cache.rds"), edges


def test_stata_save_is_a_write_edge(tmp_path: Path) -> None:
    pkg = tmp_path / "sw"
    pkg.mkdir()
    (pkg / "build.do").write_text('use raw.dta, clear\nsave "data/clean.dta", replace\n', encoding="utf-8")
    assert _find(_edges(pkg), kind="write", dst_ends="clean.dta")


# --- negative cases: the real deliverable ------------------------------------------------------

def test_comment_does_not_create_an_edge(tmp_path: Path) -> None:
    pkg = tmp_path / "cmt"
    pkg.mkdir()
    (pkg / "a.R").write_text('x <- 1  # source("ghost.R") and read.csv("ghost.csv")\n', encoding="utf-8")
    edges = _edges(pkg)
    assert not _find(edges, dst_ends="ghost.R"), edges
    assert not _find(edges, dst_ends="ghost.csv"), edges


def test_python_local_import_edge_but_not_library(tmp_path: Path) -> None:
    pkg = tmp_path / "py"
    pkg.mkdir()
    (pkg / "main.py").write_text("import utils\nimport numpy as np\nfrom pandas import DataFrame\n", encoding="utf-8")
    (pkg / "utils.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    edges = _edges(pkg)
    imports = _find(edges, kind="import")
    assert any(e.dst.endswith("utils.py") for e in imports), imports
    # numpy / pandas are libraries, not local modules -> never an (unresolved) include edge
    assert not any("numpy" in e.dst or "pandas" in e.dst for e in edges), edges


def test_fully_dynamic_path_makes_no_edge(tmp_path: Path) -> None:
    pkg = tmp_path / "dyn"
    pkg.mkdir()
    # no string literal with a filename extension -> nothing to name, so no edge (not a false miss)
    (pkg / "a.R").write_text('source(paste0(dir, scriptname))\n', encoding="utf-8")
    assert not _find(_edges(pkg), kind="source")


def test_formula_literal_is_not_mistaken_for_a_file(tmp_path: Path) -> None:
    pkg = tmp_path / "frm"
    pkg.mkdir()
    # the only string literal is a formula, not a path -> read_csv here has no filename to resolve
    (pkg / "a.R").write_text('m <- lm("y ~ x", data = d)\n', encoding="utf-8")
    assert not _find(_edges(pkg), kind="read")
