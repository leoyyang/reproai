from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

_MESSY_FILES = {
    "scripts/analysis.do": textwrap.dedent(
        """\
        * messy on purpose
        use /home/author/secret/panel.dta, clear
        foreach y in inc educ {
          reghdfe `y' treat L.gdp i.year*, absorb(id) cluster(id)
          esttab using "Table2.csv", replace
        }
        reg inc treat
        """
    ),
    "scripts/master.do": 'do "scripts/extra.do"\ndo "scripts/helper_missing.do"\n',
    "scripts/extra.do": textwrap.dedent(
        """\
        clear all
        reghdfe wage educ, absorb(id)
        merge cow year using "Other.dta"
        """
    ),
    "load_data.do": 'capture noisily use "final2.dta", clear\nif _rc != 0 {\n    use "final.dta", clear\n}\nreg y x\n',
    "final.dta": "x\n1\n",
    "final2.dta": "x\n2\n",
    "model.R": 'library(rgdal)\nlibrary(fixest)\nm <- feols(y ~ x, data = df)\nstargazer(m,\n  dep.var.labels = "Y",\n  out = "T.tex"))\n  extra = 1)\n',
    "report.R": "```{r}\nlibrary(fixest)\nm <- feols(y~x, df)\n```\n",
    "data/panel.csv": "id,year,inc\n1,2000,5\n",
}

_CLEAN_FILES = {
    "master.do": textwrap.dedent(
        """\
        version 17
        use data/panel.dta, clear
        xtset id year
        merge 1:1 id using data/other.dta
        eststo m1: reg y x1 x2, cluster(id)
        esttab m1 using "output/tables/Table1.csv", replace
        """
    ),
    "analysis.R": '# --> Table 1\nlibrary(fixest)\nm <- feols(y ~ x, data = df)\netable(m, file = "output/tables/table1.tex")\n',
    "data/panel_placeholder.csv": "id\n1\n",
    "README.md": "# README\n## Data Availability\n## Computational requirements\n## Instructions\n## Data Sources\n",
}


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


@pytest.fixture
def messy_pkg(tmp_path: Path) -> Path:
    return _write(tmp_path / "messy", _MESSY_FILES)


@pytest.fixture
def clean_pkg(tmp_path: Path) -> Path:
    return _write(tmp_path / "clean", _CLEAN_FILES)
