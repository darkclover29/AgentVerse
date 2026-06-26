import { useState, useEffect } from "react";
import * as api from "../api.js";

export default function Newspaper({ day }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activePage, setActivePage] = useState("front");

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getNewspaper(day)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to download newspaper telemetry.");
        setLoading(false);
      });
  }, [day]);

  if (loading) {
    return (
      <div className="card glass paper-loading" style={{ height: "480px", display: "grid", placeItems: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div className="spinner" style={{ borderTopColor: "var(--accent)" }}></div>
          <div className="font-mono text-glow" style={{ fontSize: 13, marginTop: 15, color: "var(--accent)", letterSpacing: 2 }}>
            DECRYPTING METROPOLITAN_SAMACHAR DATA STREAM...
          </div>
          <div className="muted font-mono" style={{ fontSize: 10, marginTop: 5 }}>
            PACKETS RECEIVED: {day * 17 + 82} // SYNC OK
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card glass" style={{ padding: 30, textAlign: "center", color: "var(--bad)" }}>
        <div className="font-mono" style={{ fontSize: 18, fontWeight: "bold" }}>⚠️ TELEMETRY OFFLINE</div>
        <div className="muted font-mono" style={{ marginTop: 10, fontSize: 12 }}>{error || "Unknown system mismatch"}</div>
      </div>
    );
  }

  const { edition, date, weather, pages } = data;
  const pageMap = Object.fromEntries(pages.map(p => [p.id, p]));
  const currentPage = pageMap[activePage] || pages[0];

  return (
    <div className="card glass paper-container" style={{ position: "relative" }}>
      <div className="paper-crease-overlay"></div>
      {/* Newspaper Header */}
      <header className="paper-header">
        <div className="paper-meta-top">
          <span className="edition font-mono">{edition}</span>
          <span className="price font-mono">PRICE: ₹5 // SUB: FREE</span>
          <span className="date font-mono">{date} · SIM DAY {day}</span>
        </div>
        
        <div className="paper-masthead">
          <h1>THE METROPOLITAN SAMACHAR</h1>
          <p className="paper-tagline">"The only source of unfiltered bazaar gossip and news in Sector 4"</p>
        </div>

        {/* Weather & Grid status ticker */}
        <div className="paper-weather-bar">
          <div className="w-box"><span className="w-lbl font-mono">MONSOON FLOOD:</span> <span className="w-val num">{weather.acid_rain}</span></div>
          <div className="w-box"><span className="w-lbl font-mono">AQI LEVEL:</span> <span className="w-val num">{weather.smog_density}</span></div>
          <div className="w-box"><span className="w-lbl font-mono">TRAFFIC DELAY:</span> <span className="w-val num">{weather.grid_latency}</span></div>
          <div className="w-box advisory font-mono">{weather.advisory}</div>
        </div>
      </header>

      {/* Pages Switcher Navigation */}
      <nav className="paper-nav">
        {pages.map((p) => (
          <button
            key={p.id}
            className={`paper-nav-tab ${activePage === p.id ? "active" : ""}`}
            onClick={() => setActivePage(p.id)}
          >
            {p.title}
          </button>
        ))}
      </nav>

      {/* Main Newspaper Body Content */}
      <main className="paper-body">
        {/* Render Front Page */}
        {activePage === "front" && (
          <div className="paper-page-grid front-page">
            <div className="paper-column main-story">
              {currentPage.articles.map((art, idx) => (
                <article key={idx} className="lead-article">
                  <h2 className="article-title">{art.title}</h2>
                  <div className="article-meta font-mono"><span className="author-badge">BY {art.author.toUpperCase()}</span> · [CITY BUREAU]</div>
                  <div className="article-content">
                    <p className="lead-para">
                      <span className="drop-cap">{art.body.charAt(0)}</span>
                      {art.body.slice(1)}
                    </p>
                  </div>
                </article>
              ))}
              
              {/* Retro Graphic Advert */}
              <div className="paper-ad-panel glitched-ad-box">
                <div className="ad-title font-mono">SPONSORED FEED // RAJU JUGAAD INC.</div>
                <div className="ad-content">
                  <span className="ad-brand">TATA MOTORS</span>
                  <span className="ad-tag font-mono">Always Moving India Forward Since 1945</span>
                </div>
              </div>
            </div>

            <div className="paper-column side-wire">
              <h3 className="section-header font-mono">CITY WIRE BULLETIN</h3>
              <div className="bulletin-list font-mono">
                {currentPage.bulletins?.map((bul, idx) => (
                  <div key={idx} className="bulletin-item">
                    <span className="bulletin-symbol">&gt;&gt;</span>
                    <span className="bulletin-text">{bul}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Render Metapolitics */}
        {activePage === "factions" && (
          <div className="paper-page-grid faction-page">
            <div className="paper-column main-story">
              {currentPage.articles.map((art, idx) => (
                <article key={idx} className="faction-article">
                  <h2 className="article-title">{art.title}</h2>
                  <div className="article-meta font-mono"><span className="author-badge">BY {art.author.toUpperCase()}</span> · [GRID MONITOR]</div>
                  <div className="article-content">
                    <p>{art.body}</p>
                  </div>
                </article>
              ))}

              {/* Mega corp neon animation widget */}
              <div className="paper-sponsor-banner font-mono">
                <div className="glitch-text" data-text="RAJU JUGAAD MOBILES">RAJU JUGAAD MOBILES</div>
                <div className="sub-text">Fix your phone screen and software. Today.</div>
              </div>
            </div>

            <div className="paper-column classifieds">
              <h3 className="section-header font-mono">CLASSIFIED LISTINGS</h3>
              <div className="classifieds-list">
                {currentPage.ads?.map((ad, idx) => (
                  <div key={idx} className="classified-ad">
                    <div className="ad-head font-mono">{ad.title}</div>
                    <div className="ad-tagline font-mono">{ad.tagline}</div>
                    <div className="ad-desc">{ad.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Render Local Scandals */}
        {activePage === "scandals" && (
          <div className="paper-page-grid scandals-page">
            <div className="paper-column main-story">
              {currentPage.articles.map((art, idx) => (
                <article key={idx} className="opinion-article">
                  <h2 className="article-title">{art.title}</h2>
                  <div className="article-meta font-mono"><span className="author-badge">BY {art.author.toUpperCase()}</span> · [THE CYNIC'S CORNER]</div>
                  <div className="article-content">
                    <p>{art.body}</p>
                  </div>
                </article>
              ))}
            </div>

            <div className="paper-column gossip">
              <h3 className="section-header font-mono">CHAI TAPRI CHATTER</h3>
              <div className="gossip-list">
                {currentPage.gossip?.map((gos, idx) => (
                  <div key={idx} className="gossip-item font-mono">
                    <span className="gossip-dot"></span>
                    <span className="gossip-text">{gos}</span>
                  </div>
                ))}
                {(!currentPage.gossip || currentPage.gossip.length === 0) && (
                  <div className="muted font-mono" style={{ padding: 10 }}>NO CHAI TAPRI CHATTER OVERHEARD TODAY.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="paper-footer font-mono">
        <span>© 2026 THE METROPOLITAN SAMACHAR MEDIA GROUP. ALL RIGHTS RESERVED.</span>
        <span>INDEX // SECTOR_4_WARD_12</span>
      </footer>
    </div>
  );
}
