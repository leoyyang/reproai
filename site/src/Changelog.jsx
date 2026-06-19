import React from "react";
import { Nav, Footer, withCode } from "./shared.jsx";
import { changelog } from "./changelog-data.js";

// "0.4.0" → "v0.4.0"; a worded label like "Initial release" is shown as-is
const versionLabel = (v) => (/^\d/.test(v) ? `v${v}` : v);

const tagClass = { New: "new", Improved: "improved", Fixed: "fixed" };

function Release({ r }) {
  return (
    <article className="release card">
      <span className="redline" />
      <div className="release-head">
        <h3 className="release-version">{versionLabel(r.version)}</h3>
        <span className="release-date">{r.date}</span>
      </div>
      {r.title && <p className="release-title">{r.title}</p>}
      <ul className="release-changes">
        {r.changes.map((c, i) => (
          <li key={i}>
            <span className={`pill ${tagClass[c.tag] || ""}`}>{c.tag}</span>
            <span className="change-text">{withCode(c.text)}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export default function Changelog() {
  const c = changelog;
  return (
    <div id="top">
      <div className="bg-grid" aria-hidden="true" />
      <Nav home={false} />
      <main className="section changelog">
        <div className="section-head">
          <h2>{c.head.lead} <span className="red">{c.head.emphasis}</span></h2>
          {c.head.sub && <p>{withCode(c.head.sub)}</p>}
        </div>
        <div className="releases">
          {c.releases.map((r) => (
            <Release key={`${r.version}-${r.date}`} r={r} />
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
