import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

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

const STAGES = [
  { name: "/reproai:check", note: "Static pre-diagnose — scans, applies rules + venue, writes the advisory" },
  { name: "/reproai:comply", note: "Venue compliance checklist (AEA, APSR, AJPS, JOP…)" },
  { name: "/reproai:fix", note: "Rewrites the recommended fixes to a copy, re-checks" },
  { name: "/reproai:debug", note: "Smoke-tests the copy — does it run? tables + figures emitted?", runs: true },
];

function EnginePanel() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActive((a) => (a + 1) % STAGES.length), 1100);
    return () => clearInterval(id);
  }, []);

  const container = {
    hidden: { opacity: 0, y: 24 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut", staggerChildren: 0.08, delayChildren: 0.15 } },
  };
  const item = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

  return (
    <motion.div
      className="engine"
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.3 }}
    >
      <span className="glow glow-a" aria-hidden="true" />
      <span className="glow glow-b" aria-hidden="true" />

      <div className="engine-head">
        <div className="lights"><i className="l r" /><i className="l y" /><i className="l g" /></div>
        <span className="engine-title">ReproAI · the per-package workflow</span>
      </div>

      <motion.div className="engine-body" variants={container}>
        <motion.div className="engine-block input" variants={item}>
          <div className="block-label">Input</div>
          <div className="block-text">A messy working directory + the draft paper</div>
        </motion.div>

        <motion.div className="engine-stages" variants={item}>
          {STAGES.map((s, i) => (
            <div className={`stage ${active === i ? "on" : ""}`} key={s.name}>
              <span className="stage-tick" />
              <div className="stage-text">
                <div className="stage-name">
                  <code className="stage-cmd">{s.name}</code>
                  {s.runs && <span className="stage-tag">runs code</span>}
                </div>
                <div className="stage-note">{s.note}</div>
              </div>
              {active === i && <span className="stage-run">working…</span>}
            </div>
          ))}
        </motion.div>

        <motion.div className="engine-block output" variants={item}>
          <div className="block-label">Output · priority-graded advisory</div>
          <ul className="advisory">
            <li><span className="pill p0">P0</span> Guarded fallback loads the wrong dataset</li>
            <li><span className="pill p1">P1</span> Declare the software version</li>
            <li><span className="pill p3">P3</span> Group commands by the table they build</li>
          </ul>
        </motion.div>

        <motion.div className="engine-evolve" variants={item}>
          <span className="evolve-dot" aria-hidden="true" />
          <div className="evolve-text">
            <code className="stage-cmd">/reproai:update</code>
            <span className="evolve-note">Outside the per-package flow — the rule set keeps evolving as more packages are seen.</span>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function Hero() {
  return (
    <header id="overview" className="hero section">
      <div className="hero-left">
        <div className="eyebrow">Author-facing plugin for replication packages</div>
        <h1>
          Build a package<br />others can <span className="red">REPRODUCE</span>.
        </h1>
        <p className="lede">
          ReproAI is a plugin that helps authors construct a cleaner, more readable replication
          package before submission — so a journal&apos;s data editor or associate editor can reproduce
          the results with far less friction. Its static commands pre-diagnose your package and
          rewrite a copy; an optional smoke test then confirms the copy actually runs. It never
          judges whether your results are correct — that stays your science.
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

function Term({ lines }) {
  return (
    <div className="term">
      {lines.map((line, i) => (
        <div className="term-line" key={i}>
          {line.length === 0 ? "\u00a0" : line.map((tok, j) => (
            <span key={j} className={`tk ${tok.c || ""}`}>{tok.t}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

const P = (t) => ({ t, c: "prompt" });
const CMD = (t) => ({ t, c: "cmd" });
const SLASH = (t) => ({ t, c: "slash" });
const FLAG = (t) => ({ t, c: "flag" });
const OUT = (t) => ({ t, c: "out" });
const TXT = (t) => ({ t });

function Bib({ lines }) {
  return (
    <div className="term">
      {lines.map((line, i) => (
        <div className="term-line" key={i}>
          {line.length === 0 ? "\u00a0" : line.map((tok, j) => (
            <span key={j} className={`tk ${tok.c || ""}`}>{tok.t}</span>
          ))}
        </div>
      ))}
    </div>
  );
}
const AT = (t) => ({ t, c: "bib-at" });
const KEY = (t) => ({ t, c: "bib-key" });
const FLD = (t) => ({ t, c: "bib-field" });
const VAL = (t) => ({ t, c: "bib-val" });
const PUN = (t) => ({ t, c: "bib-pun" });

function Install() {
  const installLines = [
    [P("$ "), CMD("cd"), TXT(" ~/my-replication-package")],
    [P("$ "), CMD("claude")],
    [],
    [P("❯ "), SLASH("/plugin marketplace add"), TXT(" leoyyang/reproai")],
    [OUT("✓ Added marketplace: reproai")],
    [],
    [P("❯ "), SLASH("/plugin install"), TXT(" reproai@reproai "), FLAG("--scope project")],
    [OUT("✓ Installed reproai — ready to use")],
  ];
  const runLines = [
    [P("❯ "), SLASH("/reproai:check"), TXT(" . "), FLAG("--venue aea")],
    [OUT("  advisory: P0=1 P1=1 P3=2")],
    [OUT("  venue (aea): 2 pass / 2 fail / 5 action")],
    [P("❯ "), SLASH("/reproai:fix"), TXT(" . "), OUT("# rewrite to a copy")],
    [P("❯ "), SLASH("/reproai:debug"), TXT(" "), OUT("# smoke-test the copy: does it run?")],
    [OUT("  ✓ runs clean · tables + figures emitted")],
  ];
  return (
    <section id="install" className="section">
      <SectionHead lead="Install" emphasis="ReproAI" sub="ReproAI ships as a plugin. Add the marketplace, install it, and run it inside your replication package." />
      <div className="cards two">
        <div className="card">
          <span className="redline" />
          <h3>Install as a plugin</h3>
          <p>Activate ReproAI inside your replication package. Use <code>--scope project</code> to keep the plugin scoped to this package.</p>
          <Term lines={installLines} />
        </div>
        <div className="card">
          <span className="redline" />
          <h3>Pre-diagnose, fix, smoke-test</h3>
          <p><code>check</code>, <code>comply</code> and <code>fix</code> are static — they read your package and rewrite a copy without running anything. The optional <code>debug</code> step then runs that copy as a smoke test: does it execute end-to-end and emit its tables and figures? Every runtime fix is your call.</p>
          <Term lines={runLines} />
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
      flow: ["Reads the data-load logic", "Finds a guarded fallback that never runs", "Flags P0 — confirm the intended dataset"],
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
      <SectionHead lead="What ReproAI helps you" emphasis="fix" sub="Recurring, author-preventable patterns that make a package harder for a data editor to reproduce — distilled from a large body of replication work, graded P0–P4 by how much each one costs a downstream run." />
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
      a: "Only when you ask it to. The three core commands — check, comply, and fix — are fully static: they inspect your files, structure, and dependencies and rewrite a copy, but never execute your analysis. The one command that runs your code is the optional debug command, and only as a smoke test (see below).",
    },
    {
      q: "What does the debug command do?",
      a: "It trial-runs a copy of your package as a smoke test — it confirms the package executes end-to-end and that the table and figure outputs actually get written. It never compares a number to your paper and never issues a 'reproducible' verdict. On a runtime error it does not silently auto-fix: it explains the root cause, offers a few options, and asks you to choose. It only ever runs the copy, never your original.",
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
      a: "No — and ReproAI says so. The plugin maximizes the probability of a first-try pass by removing known, avoidable failures before a data editor ever runs the package. Numerical match, full environment reconstruction, and runtime behavior only surface at execution, so a guarantee wouldn't be honest.",
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
  const bibLines = [
    [AT("@article"), PUN("{"), KEY("reproai2026"), PUN(",")],
    [TXT("  "), FLD("title"), TXT("   "), PUN("= {"), VAL("ReproAI: Author-Facing Pre-Diagnose for Replication Packages"), PUN("},")],
    [TXT("  "), FLD("author"), TXT("  "), PUN("= {"), VAL("ReproAI"), PUN("},")],
    [TXT("  "), FLD("year"), TXT("    "), PUN("= {"), VAL("2026"), PUN("},")],
    [TXT("  "), FLD("note"), TXT("    "), PUN("= {"), VAL("https://github.com/leoyyang/reproai"), PUN("}")],
    [PUN("}")],
  ];
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
          <Bib lines={bibLines} />
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
        <div className="footer-note">The plugin authors run before submission.</div>
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
