import React, { useState } from "react";

const GH = "https://github.com/leoyyang/reproai";

function Nav() {
  const links = ["Overview", "Install", "Examples", "FAQ", "Cite"];
  return (
    <nav className="nav">
      <a className="brand" href="#top">
        <span className="brand-mark">R</span>
        <span className="brand-name">ReproAI</span>
      </a>
      <div className="nav-links">
        {links.map((l) => (
          <a key={l} href={`#${l.toLowerCase()}`}>{l}</a>
        ))}
      </div>
    </nav>
  );
}

function EnginePanel() {
  const stages = [
    { name: "Architect", note: "Recovers workflow, maps tables, flags orphans" },
    { name: "Provisioner", note: "Pins the environment, vendors dependencies" },
    { name: "Complier", note: "Checks the target-venue standard" },
    { name: "Reviewer", note: "Cross-checks findings (deterministic)" },
  ];
  return (
    <div className="engine">
      <div className="engine-head">
        <span className="dot" /> ReproAI engine · static, no execution
      </div>
      <div className="engine-body">
        <div className="engine-block input">
          <div className="block-label">Input</div>
          <div className="block-text">A messy working directory + the draft paper</div>
        </div>
        <div className="engine-stages">
          {stages.map((s) => (
            <div className="stage" key={s.name}>
              <span className="stage-tick" />
              <div>
                <div className="stage-name">{s.name}</div>
                <div className="stage-note">{s.note}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="engine-block output">
          <div className="block-label">Output · priority-graded advisory</div>
          <ul className="advisory">
            <li><span className="pill p0">P0</span> Guarded fallback loads the wrong dataset</li>
            <li><span className="pill p1">P1</span> Declare the software version</li>
            <li><span className="pill p3">P3</span> Group commands by the table they build</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function Hero() {
  return (
    <header id="overview" className="hero section">
      <div className="hero-left">
        <div className="eyebrow">Author-facing replication pre-diagnose</div>
        <h1>
          Reproducible <span className="red">SCIENCE</span>,<br />before <span className="red">SUBMISSION</span>.
        </h1>
        <p className="lede">
          ReproAI runs on your own paper before you submit. It audits and reorganizes your
          replication package — entry points, structure, environment, venue compliance — so a
          downstream reproducibility check passes on the first try. It never runs your code and
          never judges the correctness of your results.
        </p>
        <div className="cta">
          <a className="btn primary" href={GH}>View on GitHub</a>
          <a className="btn ghost" href="#install">How to install</a>
        </div>
        <div className="hero-meta">
          <span className="dot" /> Works with Claude Code &amp; OpenAI Codex CLI
        </div>
      </div>
      <div className="hero-right">
        <EnginePanel />
      </div>
    </header>
  );
}

function Install() {
  return (
    <section id="install" className="section">
      <SectionHead lead="Install" emphasis="ReproAI" sub="It ships as a plugin. Add the marketplace, install, and run it in your package project." />
      <div className="cards two">
        <div className="card">
          <span className="redline" />
          <h3>Install as a plugin</h3>
          <p>Activate ReproAI in your package project. Use <code>--scope project</code> to keep it scoped to this package.</p>
          <pre className="term">
{`$ cd ~/my-replication-package
$ claude
❯ /plugin marketplace add leoyyang/reproai
✓ Added marketplace: reproai
❯ /plugin install reproai@reproai --scope project
✓ Installed reproai — ready to use`}
          </pre>
        </div>
        <div className="card">
          <span className="redline" />
          <h3>Run the pre-diagnose</h3>
          <p>Point it at your package. It writes a priority-graded advisory, a venue-compliance report, and a risk register — and applies only safe fixes to a copy.</p>
          <pre className="term">
{`❯ /reproai-check . --venue aea
  advisory: P0=1 P1=1 P3=2
  venue (aea): 2 pass / 2 fail / 5 action
❯ /reproai-fix .            # dry-run, copy only
❯ /reproai-comply --venue ajps`}
          </pre>
        </div>
      </div>
    </section>
  );
}

function SectionHead({ lead, emphasis, sub }) {
  return (
    <div className="section-head">
      <h2>{lead} <span className="red">{emphasis}</span></h2>
      {sub && <p>{sub}</p>}
    </div>
  );
}

function Examples() {
  const items = [
    {
      title: "Wrong dataset loads silently",
      flow: ["Architect reads the load logic", "Finds a guarded fallback that never runs", "Flags P0 — confirm the intended dataset"],
      out: "Catches a defect that would make every number run on the wrong data.",
    },
    {
      title: "Package won't run as shipped",
      flow: ["Scans entry points & dependencies", "Finds a referenced file that isn't there", "Flags the missing data / broken include"],
      out: "Surfaces the blockers that stall a reproducibility run up front.",
    },
    {
      title: "Version-fragile code",
      flow: ["Detects deprecated syntax & removed packages", "Notes a missing version declaration", "Proposes the standard, durable form"],
      out: "Prevents cross-version drift before it costs a fix-loop round.",
    },
    {
      title: "Venue compliance",
      flow: ["Loads the target-venue profile", "Checks README, structure, forms", "Lists what passes vs needs author action"],
      out: "Tells you exactly what to do before depositing to AEA, APSR, AJPS, JOP…",
    },
  ];
  return (
    <section id="examples" className="section">
      <SectionHead lead="What it" emphasis="catches" sub="Recurring, author-preventable patterns distilled from a large body of replication work — graded P0–P4 by how much they cost a downstream run." />
      <div className="cards four">
        {items.map((it) => (
          <div className="card" key={it.title}>
            <span className="redline" />
            <h3>{it.title}</h3>
            <ol className="flow">
              {it.flow.map((f, i) => <li key={i}>{f}</li>)}
            </ol>
            <div className="card-out">{it.out}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FAQ() {
  const qa = [
    {
      q: "Does ReproAI run my code?",
      a: "No. ReproAI is static — it inspects your files, structure, and dependencies, but never executes your analysis. It also never issues a reproducibility verdict; it only advises. The downstream execution-based check is a separate step.",
    },
    {
      q: "Which venues does it support?",
      a: "It ships profiles for AEA (AER, AEJ, JEL, JEP), the Econometric Society, APSR, AJPS, and JOP, plus generic Dataverse and openICPSR fallbacks. Profiles are data files, so the list grows over time.",
    },
    {
      q: "What does P0–P4 mean?",
      a: "Findings are graded by their downstream reproducibility cost: P0 blocks reproduction, P1 is a large cost (many fix-loop rounds), P2 is moderate misread risk, P3 is minor organization, P4 is venue polish. You can fix P0 only, P0+P1, or all.",
    },
    {
      q: "Will fixing everything guarantee a first-try pass?",
      a: "No — and ReproAI says so. Pre-diagnose maximizes the probability of a first-try pass by removing known, avoidable failures. Numerical match, full environment reconstruction, and runtime behavior only surface at execution, so a guarantee isn't honest.",
    },
    {
      q: "Does it auto-fix my files?",
      a: "Only the small set of fixes that are provably semantics-preserving, and only to a copy — never your original, dry-run by default. Anything that could change a result is propose-only, left for you to apply.",
    },
    {
      q: "Which tools does it work with?",
      a: "It runs as a plugin in Claude Code and OpenAI Codex CLI, and the engine is a plain command-line tool, so any host that can call a shell can use it.",
    },
  ];
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="section">
      <SectionHead lead="Frequently asked" emphasis="questions" />
      <div className="faq">
        {qa.map((item, i) => (
          <div className={`faq-item ${open === i ? "open" : ""}`} key={i}>
            <button className="faq-q" onClick={() => setOpen(open === i ? -1 : i)}>
              <span>{item.q}</span>
              <span className="faq-sign">{open === i ? "−" : "+"}</span>
            </button>
            {open === i && <div className="faq-a">{item.a}</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Cite() {
  const bib = `@article{reproai2026,
  title   = {ReproAI: Author-Facing Pre-Diagnose for Replication Packages},
  author  = {ReproAI},
  year    = {2026},
  note    = {https://github.com/leoyyang/reproai}
}`;
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(bib).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <section id="cite" className="section">
      <SectionHead lead="Cite" emphasis="ReproAI" sub="If ReproAI helps your work, please cite it." />
      <div className="cards two">
        <div className="card">
          <span className="redline" />
          <div className="cite-label">Reference</div>
          <h3 className="cite-title">ReproAI: Author-Facing Pre-Diagnose for Replication Packages</h3>
          <p className="cite-meta">reproAI project · 2026</p>
          <a className="link" href={GH}>github.com/leoyyang/reproai →</a>
        </div>
        <div className="card">
          <span className="redline" />
          <div className="cite-label-row">
            <div className="cite-label">BibTeX</div>
            <button className="copy" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
          </div>
          <pre className="bib">{bib}</pre>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="brand">
          <span className="brand-mark">R</span>
          <span className="brand-name">ReproAI</span>
        </div>
        <div className="footer-links">
          <a href={GH}>GitHub</a>
          <a href="#cite">Cite</a>
        </div>
        <div className="footer-note">Reproducibility, settled before submission.</div>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <div id="top">
      <div className="bg-grid" aria-hidden="true" />
      <Nav />
      <Hero />
      <Install />
      <Examples />
      <FAQ />
      <Cite />
      <Footer />
    </div>
  );
}
