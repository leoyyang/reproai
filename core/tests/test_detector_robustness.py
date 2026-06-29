"""Robustness tests for three detector fixes (branch fix/detector-robustness).

FIX #4 — `_GRAPH_EXPORT` had drifted from dependency_graph's graphics-device list, so a jpeg/tiff/
         svg/cairo-only figure read as "missing export" forever and /reproai:fix could only clear it
         by rewriting the device to pdf() (lossy). Drift-guard below fails CI if the two ever diverge.
FIX #5 — the `# --> Table N` anchor reproai itself recommends was not matched by `_TABLE_HEADER` /
         `_FIGURE_HEADER`, so A12 fired forever even after the author followed the guidance. Invariant
         below: "the format reproai recommends clears the check it recommends it for."
FIX #6 — B4 (and the whole line-by-line detector class) scanned RAW lines, so an absolute path /
         pattern left inside a comment — including by reproai's OWN /fix output — kept firing. Test
         pairs pin BOTH directions: silent on a commented hit, still firing on real code (incl. a
         trailing comment). NIT-1: Stata `'` is macro syntax, not a string delimiter, so an odd number
         of `` `macro' `` apostrophes before an inline `//` must not mask the comment marker away.
"""
from __future__ import annotations

import re
from pathlib import Path

from line1_core import coordinator
from line1_core import dependency_graph as dg
from line1_core.rule_engine import (
    _FIGURE_HEADER,
    _GRAPH_EXPORT,
    _TABLE_HEADER,
    _mask_string_contents,
    _strip_comment_keep_strings,
    load_rules,
)


def _fired(root: Path, venue: str | None = None) -> set[str]:
    return {it["rule_id"] for it in coordinator.check(root, venue)["advisory_plan"]["items"]}


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


# ============================ FIX #4: graphics-device coverage ============================

# The graphics-device subset of dependency_graph._WRITE_VERBS (the verbs that OPEN a plotting device
# or save a figure), as opposed to the table/data writers in the same tuple. Derived structurally so
# this stays correct if the tuple grows: a write verb is a graphics device iff it is NOT a known
# data/table writer.
_DATA_TABLE_WRITE_VERBS = frozenset({
    "write.csv", "write.csv2", "write.table", "write_csv", "write_tsv", "write_delim", "fwrite",
    "saveRDS", "save", "write_rds", "write_dta", "write.dta", "write.dta13", "write_xlsx", "st_write",
    "stargazer", "etable", "texreg", "htmlreg", "modelsummary",
    "to_csv", "to_stata", "to_parquet", "to_excel", "to_pickle",
})


def _graphics_devices_in_dependency_graph() -> list[str]:
    return [v for v in dg._WRITE_VERBS if v not in _DATA_TABLE_WRITE_VERBS]


def test_graph_export_covers_dependency_graph_devices() -> None:
    """DRIFT GUARD: every graphics-device verb dependency_graph treats as a figure writer must be
    matched by rule_engine._GRAPH_EXPORT. If a device is ever added to dependency_graph._WRITE_VERBS
    but not to _GRAPH_EXPORT, this fails — the exact regression FIX #4 repairs (jpeg/tiff/svg/cairo
    were figure writers in the graph but invisible to the gate + rule D1)."""
    devices = _graphics_devices_in_dependency_graph()
    # sanity: the structural filter actually leaves the known device verbs (not an empty set)
    assert {"pdf", "png", "jpeg", "tiff", "svg", "cairo_pdf"} <= set(devices), devices
    missing = [v for v in devices if not _GRAPH_EXPORT.search(f'{v}("out.ext")')]
    assert not missing, (
        f"_GRAPH_EXPORT omits graphics device(s) that dependency_graph considers figure writers: "
        f"{missing}. Add the token (escaping '(' as '\\\\(') to _GRAPH_EXPORT in rule_engine.py."
    )


def test_graph_export_matches_expanded_device_family() -> None:
    """The empirically-validated device family FIX #4 introduced (jpeg/tiff/bmp/svg/svglite/cairo_*/
    bitmap/agg_*/Cairo*/tikz) is matched."""
    for call in [
        'jpeg("f.jpg")', 'jpg("f")', 'tiff("f")', 'bmp("f")', 'svg("f")', 'svglite("f")',
        'cairo_pdf("f")', 'cairo_ps("f")', 'bitmap("f")', 'agg_png("f")', 'agg_jpeg("f")',
        'agg_tiff("f")', 'Cairo("f")', 'CairoPNG("f")', 'CairoPDF("f")', 'CairoJPEG("f")',
        'CairoTIFF("f")', 'tikz("f")', 'postscript("f")', 'savefig("f.png")',
        'pdf("f")', 'png("f")', 'ggsave("f.png")', 'graph export f.png', 'gr export f.eps',
    ]:
        assert _GRAPH_EXPORT.search(call), f"_GRAPH_EXPORT should match {call!r}"


def test_graph_export_preserves_legacy_matches() -> None:
    """The single leading `\\b` (deliberately NOT per-token) preserves the OLD regex's behavior:
    `pdf(`/`png(`/`postscript(`/`graph export`/`dev.copy` all still match. This is the
    'preserve every previously-matched device' guard."""
    for call in ['pdf("f")', 'png("f")', 'postscript("f")', 'graph export "f.eps"',
                 'graph save g', 'ggsave("f")', 'dev.copy(pdf)']:
        assert _GRAPH_EXPORT.search(call), f"legacy match lost for {call!r}"


def test_jpeg_only_figure_export_satisfies_d1(tmp_path: Path) -> None:
    """END TO END: a top-level figure with a jpeg() export under output/figures/ must NOT fire D1
    'missing export'. Before FIX #4 jpeg() was invisible, so D1 fired and /fix could only clear it by
    converting the device to pdf() (lossy)."""
    pkg = _write(tmp_path / "jpeg_fig", {
        "fig.R": '# --> Figure 1\nlibrary(ggplot2)\nggplot(df, aes(x, y)) + geom_point()\n'
                 'jpeg("output/figures/figure_1.jpg")\nprint(last_plot())\ndev.off()\n',
    })
    assert "D1-output-artifact-coverage" not in _fired(pkg)


def test_figure_without_any_export_still_fires_d1(tmp_path: Path) -> None:
    """Control for the above: a top-level figure producer with NO export still fires D1."""
    pkg = _write(tmp_path / "no_fig_export", {
        "fig.R": '# --> Figure 1\nlibrary(ggplot2)\nggplot(df, aes(x, y)) + geom_point()\n',
    })
    assert "D1-output-artifact-coverage" in _fired(pkg)


def test_d1_target_form_does_not_steer_device_conversion() -> None:
    """FIX #4 step 4: D1's target_form must not hardcode a pdf example that nudges /fix toward
    swapping the author's device. It should keep the format lossless (use the author's existing
    device/format)."""
    rules = {r["id"]: r for r in load_rules()}
    tf = rules["D1-output-artifact-coverage"]["target_form"]
    assert "figure_N.pdf" not in tf, "D1 target_form still hardcodes figure_N.pdf (lossy device nudge)"
    assert "existing device" in tf.lower() or "never convert" in tf.lower(), (
        "D1 target_form should explicitly tell the LLM to keep the author's device/format"
    )


# ============================ FIX #5: recommended anchor clears A12 ============================

def test_table_header_matches_recommended_anchor() -> None:
    """The detector must match the exact anchor reproai recommends: `# --> Table 1` / `# --> Figure 2`
    (and the `*`/`//` comment + `->`/`=>` variants)."""
    for s in ["# --> Table 1", "* --> Table 1", "* -> Table 2", "# => Table 3", "// --> Table 4"]:
        assert _TABLE_HEADER.match(s), f"_TABLE_HEADER should match recommended anchor {s!r}"
    for s in ["# --> Figure 2", "* --> Figure 1", "* -> Fig. 3", "# => Figura 2"]:
        assert _FIGURE_HEADER.match(s), f"_FIGURE_HEADER should match recommended anchor {s!r}"
    # plain (no-arrow) headers must still match — Option B EXTENDS, never narrows
    assert _TABLE_HEADER.match("* Table 3")
    assert _FIGURE_HEADER.match("# Figure 2")


def test_table_header_rejects_long_arrows_bullets_hrules() -> None:
    """Adversarial: a long arrow, a bullet, and a comment hrule must NOT be read as a Table anchor."""
    for s in ["# ----> Table 1", "# - Table 1", "# ---- Table 1", "# ----", "# >> Table 1"]:
        assert not _TABLE_HEADER.match(s), f"_TABLE_HEADER must NOT match {s!r}"


def test_recommended_anchor_clears_a12(tmp_path: Path) -> None:
    """INVARIANT: the format reproai recommends clears the check it recommends it for. Following the
    documented `# --> Table N` anchor must silence A12. Before FIX #5, A12 fired forever even after
    the author did exactly what the guidance said."""
    pkg = _write(tmp_path / "anchored", {
        "a.R": "# --> Table 1\nlibrary(fixest)\n"
               "m1 <- feols(y ~ x, df)\nm2 <- feols(z ~ x, df)\n"
               'etable(m1, m2, file = "output/tables/t1.tex")\n',
    })
    assert "A12-table-comment-mapping" not in _fired(pkg)


def test_a12_still_fires_without_anchor(tmp_path: Path) -> None:
    """Control: same two estimations with NO anchor still fire A12 (the fix only adds the arrow slot;
    it does not suppress the rule)."""
    pkg = _write(tmp_path / "unanchored", {
        "a.R": "library(fixest)\nm1 <- feols(y ~ x, df)\nm2 <- feols(z ~ x, df)\n",
    })
    assert "A12-table-comment-mapping" in _fired(pkg)


_ANCHOR_IN_GUIDANCE = re.compile(r'([-=]{1,2}>)\s*(Table|Figure)\s+', re.IGNORECASE)


def test_detector_matches_anchor_example_in_yaml() -> None:
    """BONUS (strongest drift guard): read the arrow-anchor example straight out of the A12/D1 rule
    guidance and assert the detector matches it — so the YAML guidance and the detector can never
    diverge again. If someone changes the recommended anchor in the YAML, the detector must follow."""
    rules = {r["id"]: r for r in load_rules()}
    blobs: list[str] = []
    for rid in ("A12-table-comment-mapping", "D1-output-artifact-coverage", "A2-table-grouping"):
        r = rules.get(rid)
        if not r:
            continue
        blobs += [str(r.get("rule", "")), str(r.get("target_form", "")), str(r.get("detection", ""))]
    checked = 0
    for blob in blobs:
        for arrow, kind in _ANCHOR_IN_GUIDANCE.findall(blob):
            # reconstruct the anchor the guidance shows, as a comment line, and assert it matches
            line = f"* {arrow} {kind} 1"
            rx = _FIGURE_HEADER if kind.lower().startswith("fig") else _TABLE_HEADER
            assert rx.match(line), (
                f"guidance shows anchor {arrow} {kind} but the detector does not match {line!r} "
                f"(guidance/detector drift)"
            )
            checked += 1
    assert checked > 0, "expected at least one `--> Table/Figure` anchor example in the A12/D1 guidance"


# ============================ FIX #6: comment-aware scanning ============================

def test_b4_silent_on_comment_only_abs_path(tmp_path: Path) -> None:
    """The reproai /fix non-convergence bug: a `# was: setwd("/Users/...")` breadcrumb left by /fix
    itself must NOT keep tripping B4."""
    pkg = _write(tmp_path / "b4_comment", {
        "a.R": '# was: setwd("/Users/foo/proj")\nd <- read.csv("data/x.csv")\nm <- lm(y ~ x, d)\n',
    })
    assert "B4-no-abs-paths" not in _fired(pkg)


def test_b4_fires_on_real_abs_path_with_trailing_comment(tmp_path: Path) -> None:
    """OVER-MASKING GUARD: a real abs path inside a string with a trailing comment MUST still fire.
    The fix strips the comment but PRESERVES the string literal, so B4 keeps catching its real case."""
    pkg = _write(tmp_path / "b4_real", {
        "a.R": 'd <- read.csv("/home/me/d.csv")  # local override\nm <- lm(y ~ x, d)\n',
    })
    assert "B4-no-abs-paths" in _fired(pkg)


def test_b4_silent_on_stata_leading_star_comment(tmp_path: Path) -> None:
    """Stata variant: a leading `*` comment containing an abs path must NOT fire B4."""
    pkg = _write(tmp_path / "b4_stata_comment", {
        "a.do": "* setwd is /Users/foo\nuse data.dta, clear\nreg y x\n",
    })
    assert "B4-no-abs-paths" not in _fired(pkg)


def test_b4_fires_on_stata_real_abs_path(tmp_path: Path) -> None:
    """Stata variant control: a real hardcoded abs path still fires B4."""
    pkg = _write(tmp_path / "b4_stata_real", {
        "a.do": 'use "/Users/foo/panel.dta", clear\nreg y x\n',
    })
    assert "B4-no-abs-paths" in _fired(pkg)


def test_a4_silent_on_commented_ts_operator(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "a4_comment", {
        "a.do": "use d.dta, clear\n* uses L.gdp later\nreg y x\n",
    })
    assert "A4-panel-declare" not in _fired(pkg)


def test_a4_fires_on_real_ts_operator(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "a4_real", {
        "a.do": "use d.dta, clear\nreg y L.gdp\n",
    })
    assert "A4-panel-declare" in _fired(pkg)


def test_b3_silent_on_commented_wildcard(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "b3_comment", {
        "a.do": "use d.dta, clear\n* reg y x*\nreg y x\n",
    })
    assert "B3-no-wide-wildcard" not in _fired(pkg)


def test_b3_fires_on_real_wildcard(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "b3_real", {
        "a.do": "use d.dta, clear\nreg y x*\n",
    })
    assert "B3-no-wide-wildcard" in _fired(pkg)


def test_c1_silent_on_commented_github_install(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "c1_comment", {
        "a.R": '# install_github("x/y")\nlibrary(z)\nm <- lm(y ~ x, d)\n',
    })
    assert "C1-pin-deps" not in _fired(pkg)


def test_c1_fires_on_real_github_install(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "c1_real", {
        "a.R": 'remotes::install_github("x/y")\nm <- lm(y ~ x, d)\n',
    })
    assert "C1-pin-deps" in _fired(pkg)


# --- NIT-1: Stata macro apostrophes must not defeat comment stripping ---

def test_b4_silent_on_stata_macro_apostrophe_inline_comment(tmp_path: Path) -> None:
    """THE NIT-1 REPRODUCER. Stata `'` is a macro close (`` `x' ``), NOT a string delimiter. An ODD
    number of macro apostrophes left of an inline `//` must not mask the comment marker away — so an
    abs path in that comment (e.g. a `# was:` breadcrumb from /fix) must stay SILENT."""
    pkg = _write(tmp_path / "nit1_odd", {
        "a.do": "use d.dta, clear\nlocal p `x'  // was: use /Users/foo/old.dta\nreg y x\n",
    })
    assert "B4-no-abs-paths" not in _fired(pkg)


def test_b4_fires_on_stata_abs_path_in_string_with_trailing_comment(tmp_path: Path) -> None:
    """OVER-MASKING GUARD for NIT-1: a real abs path inside a genuine Stata `"..."` string, followed by
    a trailing `// comment`, MUST still fire B4. (The fix only stops treating `'` as a string opener;
    `"..."` strings are still recognized, and the original string is preserved for the match.)"""
    pkg = _write(tmp_path / "nit1_real", {
        "a.do": 'use "/Users/foo/panel.dta"  // override path\nreg y x\n',
    })
    assert "B4-no-abs-paths" in _fired(pkg)


def test_b4_silent_on_stata_even_apostrophe_inline_comment(tmp_path: Path) -> None:
    """Even-apostrophe lines were already silent (the macros paired up by accident); confirm they stay
    silent — and, with the fix, are masked correctly rather than corrupted."""
    pkg = _write(tmp_path / "nit1_even", {
        "a.do": "use d.dta, clear\ndi `a' `b'  // path /Users/foo/x.dta\nreg y x\n",
    })
    assert "B4-no-abs-paths" not in _fired(pkg)


def test_mask_string_contents_stata_treats_apostrophe_as_macro() -> None:
    """Unit guard for NIT-1: Stata masking must leave a bare `'` (macro close) verbatim so a following
    `//` stays visible, while still masking `"..."` and the compound `` `"..."' `` string forms. R /
    Python masking (both quote types) must be unchanged."""
    # Stata: macro apostrophes are NOT strings -> comment marker survives, path text intact
    assert _mask_string_contents("local p `x'  // /Users/foo/x", "stata") == "local p `x'  // /Users/foo/x"
    assert _mask_string_contents("di `a' `b'  // c", "stata") == "di `a' `b'  // c"
    # Stata: a real "..." string IS masked (so a // inside it is not a comment)
    assert _mask_string_contents('use "a//b"  // c', "stata") == 'use "xxxx"  // c'
    # Stata: compound `"..."' string masked, delimiters + length preserved
    assert _mask_string_contents('f `"a b"\' x', "stata") == 'f `"xxx"\' x'
    # R/Python UNCHANGED: both ' and " open strings
    assert _mask_string_contents("u <- '/abs/p'  # c", "r") == "u <- 'xxxxxx'  # c"
    assert _mask_string_contents('x <- "/abs"  # c', "python") == 'x <- "xxxx"  # c'


def test_strip_comment_keeps_string_literals() -> None:
    """Unit guard on the helper that makes the whole class correct: the comment is removed but a
    string literal (where _ABS_PATH reads its path) survives, including a `#`/`//` *inside* a string."""
    # R: trailing comment removed, the path string kept intact
    assert _strip_comment_keep_strings('read.csv("/home/me/d.csv")  # note', "r") == 'read.csv("/home/me/d.csv")  '
    # R: a `#` inside a string is NOT a comment
    assert _strip_comment_keep_strings('u <- "http://a#b"  # real', "r") == 'u <- "http://a#b"  '
    # Stata leading `*` -> whole line is comment
    assert _strip_comment_keep_strings("* a /Users/x note", "stata").strip() == ""
    # Stata inline `//`, but `//` inside a string is preserved
    assert _strip_comment_keep_strings('use "a.dta"  // load', "stata") == 'use "a.dta"  '
    assert _strip_comment_keep_strings('local u "http://x"', "stata") == 'local u "http://x"'
    # Stata macro apostrophe (NIT-1): `'` is not a string, so the inline `//` is still stripped
    assert _strip_comment_keep_strings("local p `x'  // c", "stata") == "local p `x'  "
    # Stata single-line /* ... */ blanked, surrounding code intact
    assert "robust" in _strip_comment_keep_strings("reg y x /* note */ , robust", "stata")
    assert "note" not in _strip_comment_keep_strings("reg y x /* note */ , robust", "stata")
    # multiplication is not a comment (only a LEADING * is)
    assert _strip_comment_keep_strings("gen z = a * b", "stata") == "gen z = a * b"
    # unknown language: returned unchanged (no false-negative risk on non-script files)
    assert _strip_comment_keep_strings("# keep /Users/x", "other") == "# keep /Users/x"
