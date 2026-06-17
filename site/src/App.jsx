import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { content, GH } from "./content.js";

// render `inline code` spans from backticks in a plain content string
function withCode(text) {
  return text.split("`").map((seg, i) =>
    i % 2 === 1 ? <code key={i}>{seg}</code> : <React.Fragment key={i}>{seg}</React.Fragment>
  );
}

function Nav() {
  return (
    <nav className="nav">
      <a className="brand" href="#top">
        <span className="brand-mark">{content.brand.mark}</span>
        <span className="brand-name">{content.brand.name}</span>
      </a>
      <div className="nav-links">
        {content.nav.links.map((l) => (
          <a key={l} href={`#${l.toLowerCase()}`}>{l}</a>
        ))}
      </div>
    </nav>
  );
}

function EnginePanel() {
  const stages = content.engine.stages;
  const [active, setActive] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setActive((a) => (a + 1) % stages.length), 1100);
    return () => clearInterval(id);
  }, [stages.length]);

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
        <span className="engine-title">{content.engine.title}</span>
      </div>

      <motion.div className="engine-body" variants={container}>
        <motion.div className="engine-block input" variants={item}>
          <div className="block-label">{content.engine.inputLabel}</div>
          <div className="block-text">{content.engine.inputText}</div>
        </motion.div>

        <motion.div className="engine-stages" variants={item}>
          {stages.map((s, i) => (
            <div className={`stage ${active === i ? "on" : ""}`} key={s.name}>
              <span className="stage-tick" />
              <div className="stage-text">
                <div className="stage-name">
                  <code className="stage-cmd">{s.name}</code>
                  {s.runs && <span className="stage-tag">{content.engine.runsTag}</span>}
                </div>
                <div className="stage-note">{s.note}</div>
              </div>
              {active === i && <span className="stage-run">{content.engine.working}</span>}
            </div>
          ))}
        </motion.div>

        <motion.div className="engine-block output" variants={item}>
          <div className="block-label">{content.engine.outputLabel}</div>
          <ul className="advisory">
            {content.engine.advisory.map((a) => (
              <li key={a.label}><span className={`pill ${a.cls}`}>{a.label}</span> {a.text}</li>
            ))}
          </ul>
        </motion.div>

        <motion.div className="engine-evolve" variants={item}>
          <span className="evolve-dot" aria-hidden="true" />
          <div className="evolve-text">
            <code className="stage-cmd">{content.engine.update.cmd}</code>
            <span className="evolve-note">{content.engine.update.note}</span>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function Hero() {
  const h = content.hero;
  return (
    <header id="overview" className="hero section">
      <div className="hero-left">
        <div className="eyebrow">{h.eyebrow}</div>
        <h1>
          {h.headline.lead}<br />{h.headline.rest}<span className="red">{h.headline.emph}</span>{h.headline.tail}
        </h1>
        <p className="lede">{withCode(h.lede)}</p>
        <div className="cta">
          <a className="btn primary" href={GH}>{h.ctaPrimary}</a>
          <a className="btn ghost" href="#install">{h.ctaGhost}</a>
        </div>
        <div className="hero-meta">
          <span className="dot" /> {h.meta}
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

function Install() {
  const c = content.install;
  return (
    <section id="install" className="section">
      <SectionHead lead={c.head.lead} emphasis={c.head.emphasis} sub={c.head.sub} />
      <div className="cards two">
        <div className="card">
          <span className="redline" />
          <h3>{c.claude.title}</h3>
          <Term lines={c.claude.lines} />
          <p className="term-note">{withCode(c.claude.note)}</p>
        </div>
        <div className="card">
          <span className="redline" />
          <h3>{c.codex.title}</h3>
          <Term lines={c.codex.lines} />
          <p className="term-note">{withCode(c.codex.note)}</p>
        </div>
      </div>
    </section>
  );
}

function Usage() {
  const c = content.usage;
  return (
    <section id="usage" className="section">
      <SectionHead lead={c.head.lead} emphasis={c.head.emphasis} sub={c.head.sub} />
      <div className="cards two">
        <div className="card">
          <span className="redline" />
          <h3>{c.card.title}</h3>
          <p>{withCode(c.card.body)}</p>
        </div>
        <div className="card">
          <span className="redline" />
          <h3>{c.demoTitle}</h3>
          <Term lines={c.runLines} />
        </div>
      </div>
    </section>
  );
}

function SectionHead({ lead, emphasis, sub }) {
  return (
    <div className="section-head">
      <h2>{lead} <span className="red">{emphasis}</span></h2>
      {sub && <p>{withCode(sub)}</p>}
    </div>
  );
}

function Examples() {
  const c = content.examples;
  return (
    <section id="examples" className="section">
      <SectionHead lead={c.head.lead} emphasis={c.head.emphasis} sub={c.head.sub} />
      <div className="cards four">
        {c.items.map((it) => (
          <div className="card" key={it.title}>
            <span className="redline" />
            <h3>{it.title}</h3>
            <ol className="flow">
              {it.flow.map((f, i) => <li key={i}>{withCode(f)}</li>)}
            </ol>
            <div className="card-out">{withCode(it.out)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FAQ() {
  const c = content.faq;
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="section">
      <SectionHead lead={c.head.lead} emphasis={c.head.emphasis} />
      <div className="faq">
        {c.qa.map((item, i) => (
          <div className={`faq-item ${open === i ? "open" : ""}`} key={i}>
            <button className="faq-q" onClick={() => setOpen(open === i ? -1 : i)}>
              <span>{item.q}</span>
              <span className="faq-sign">{open === i ? "−" : "+"}</span>
            </button>
            {open === i && <div className="faq-a">{withCode(item.a)}</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Cite() {
  const c = content.cite;
  // the copy-button text is derived from the displayed BibTeX, so the two never drift
  const bib = c.bibLines.map((line) => line.map((tok) => tok.t).join("")).join("\n");
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(bib).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <section id="cite" className="section">
      <SectionHead lead={c.head.lead} emphasis={c.head.emphasis} sub={c.head.sub} />
      <div className="cards">
        <div className="card">
          <span className="redline" />
          <div className="cite-label">{c.referenceLabel}</div>
          <h3 className="cite-title">{c.title}</h3>
          <p className="cite-meta">{c.meta}</p>
          <a className="link" href={c.linkUrl}>{c.linkText}</a>
          <div className="cite-bibtex">
            <div className="cite-label-row">
              <div className="cite-label">{c.bibtexLabel}</div>
              <button className="copy" onClick={copy}>{copied ? c.copyDone : c.copyIdle}</button>
            </div>
            <Bib lines={c.bibLines} />
          </div>
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
          <span className="brand-mark">{content.brand.mark}</span>
          <span className="brand-name">{content.brand.name}</span>
        </div>
        <div className="footer-links">
          {content.footer.links.map((l) => (
            <a key={l.label} href={l.href}>{l.label}</a>
          ))}
        </div>
        <div className="footer-note">{content.footer.note}</div>
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
      <Usage />
      <Examples />
      <FAQ />
      <Cite />
      <Footer />
    </div>
  );
}
