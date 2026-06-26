import { useMemo } from "react";

const FACTION_COLOR = {
  corp: "var(--corp)", hacker: "var(--hacker)",
  syndicate: "var(--syndicate)", unaligned: "var(--unaligned)",
};

const FACTION_NAME = {
  corp: "Authority & Netas", hacker: "IT & Side-Hustlers",
  syndicate: "Auto & Cab Cartels", unaligned: "Vendors & Citizens",
};

export default function FactionCharts({ agents = [], businesses = [], gdpHistory = [] }) {
  // 1. Calculate Wealth Distribution
  const factionWealth = useMemo(() => {
    const wealth = { corp: 0, hacker: 0, syndicate: 0, unaligned: 0 };
    agents.forEach((a) => {
      wealth[a.faction] = (wealth[a.faction] || 0) + a.wealth;
    });
    return wealth;
  }, [agents]);

  const totalWealth = useMemo(() => {
    return Object.values(factionWealth).reduce((s, w) => s + w, 0) || 1;
  }, [factionWealth]);

  // 2. Calculate Faction Presence (Agents + Open Businesses)
  const factionPresence = useMemo(() => {
    const presence = { corp: 0, hacker: 0, syndicate: 0, unaligned: 0 };
    agents.forEach((a) => {
      presence[a.faction]++;
    });
    businesses.filter(b => b.status === "open").forEach((b) => {
      const owner = agents.find(a => a.id === b.owner_id);
      const faction = owner ? owner.faction : "unaligned";
      presence[faction] += 2; // weight businesses heavier
    });
    return presence;
  }, [agents, businesses]);

  const totalPresence = useMemo(() => {
    return Object.values(factionPresence).reduce((s, p) => s + p, 0) || 1;
  }, [factionPresence]);

  // 3. Render GDP Sparkline SVG Path
  const gdpPath = useMemo(() => {
    if (gdpHistory.length < 2) return "";
    const w = 400, h = 120;
    const padding = 10;
    const maxDay = Math.max(...gdpHistory.map(d => d.day)) || 1;
    const minDay = Math.min(...gdpHistory.map(d => d.day)) || 0;
    const maxVal = Math.max(...gdpHistory.map(d => d.gdp)) * 1.05;
    const minVal = Math.min(...gdpHistory.map(d => d.gdp)) * 0.95;

    const points = gdpHistory.map(d => {
      const x = padding + ((d.day - minDay) / (maxDay - minDay || 1)) * (w - 2 * padding);
      const y = h - padding - ((d.gdp - minVal) / (maxVal - minVal || 1)) * (h - 2 * padding);
      return `${x},${y}`;
    });

    return {
      line: `M ${points.join(" L ")}`,
      area: `M ${padding},${h - padding} L ${points.join(" L ")} L ${points[points.length - 1].split(",")[0]},${h - padding} Z`
    };
  }, [gdpHistory]);

  return (
    <div className="faction-charts" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
      {/* Chart 1: GDP Trend */}
      <div className="card card-pad glass">
        <div className="card-title">City GDP (Total Assets Over Days)</div>
        {gdpHistory.length < 2 ? (
          <div className="muted" style={{ height: 120, display: "grid", placeItems: "center" }}>
            Waiting for simulation ticks...
          </div>
        ) : (
          <div style={{ position: "relative" }}>
            <svg viewBox="0 0 400 120" style={{ width: "100%", height: 120, display: "block" }}>
              <defs>
                <linearGradient id="gdpGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* Grid Lines */}
              <line x1="10" y1="60" x2="390" y2="60" stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <line x1="10" y1="110" x2="390" y2="110" stroke="rgba(255,255,255,0.05)" />
              {/* Area Path */}
              <path d={gdpPath.area} fill="url(#gdpGrad)" />
              {/* Line Path */}
              <path d={gdpPath.line} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-3)", marginTop: 4 }}>
              <span>Day {gdpHistory[0].day}</span>
              <span>Day {gdpHistory[gdpHistory.length - 1].day} (Current)</span>
            </div>
          </div>
        )}
      </div>

      {/* Chart 2: Faction Wealth distribution */}
      <div className="card card-pad glass">
        <div className="card-title">Faction Asset Distribution</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {Object.entries(factionWealth).map(([faction, wealth]) => {
            const percent = (wealth / totalWealth) * 100;
            return (
              <div key={faction} className="minibar" style={{ fontSize: 12 }}>
                <div className="ml" style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                  <span style={{ fontWeight: 600, color: FACTION_COLOR[faction] }}>{FACTION_NAME[faction]}</span>
                  <span className="num" style={{ color: "var(--text)" }}>₹{Math.round(wealth).toLocaleString()} ({Math.round(percent)}%)</span>
                </div>
                <div className="mt" style={{ background: "rgba(255,255,255,0.05)", height: 7, borderRadius: 4 }}>
                  <div style={{ width: `${percent}%`, background: FACTION_COLOR[faction], height: "100%", borderRadius: 4 }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Chart 3: Faction Presence Segment Bar */}
      <div className="card card-pad glass">
        <div className="card-title">Faction Territory Presence index</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Segment Bar */}
          <div style={{ display: "flex", height: 18, borderRadius: 6, overflow: "hidden", background: "rgba(255,255,255,0.05)" }}>
            {Object.entries(factionPresence).map(([faction, presence]) => {
              const percent = (presence / totalPresence) * 100;
              if (percent === 0) return null;
              return (
                <div
                  key={faction}
                  style={{
                    width: `${percent}%`,
                    background: FACTION_COLOR[faction],
                    height: "100%",
                    transition: "width 400ms ease"
                  }}
                  title={`${FACTION_NAME[faction]} Presence Index: ${presence}`}
                />
              );
            })}
          </div>
          {/* Legend Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {Object.entries(factionPresence).map(([faction, presence]) => {
              const percent = (presence / totalPresence) * 100;
              return (
                <div key={faction} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11.5 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: FACTION_COLOR[faction], display: "inline-block" }} />
                  <span style={{ color: "var(--text-2)" }}>{FACTION_NAME[faction]}:</span>
                  <span className="num" style={{ fontWeight: 600, color: "var(--text)" }}>{Math.round(percent)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
