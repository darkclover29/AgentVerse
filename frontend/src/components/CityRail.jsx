// Right rail of the city view: faction filter chips (with live counts) + a wealth
// distribution by faction. Clicking a faction filters the grid; click again to clear.

const FACTIONS = [
  { key: "corp", label: "Authority & Netas", color: "var(--corp)" },
  { key: "hacker", label: "IT & Side-Hustlers", color: "var(--hacker)" },
  { key: "syndicate", label: "Auto & Cab Cartels", color: "var(--syndicate)" },
  { key: "unaligned", label: "Vendors & Citizens", color: "var(--unaligned)" },
];

export default function CityRail({ agents, businesses, factionFilter, onFilter }) {
  const counts = {};
  const wealth = {};
  for (const a of agents) {
    counts[a.faction] = (counts[a.faction] || 0) + 1;
    wealth[a.faction] = (wealth[a.faction] || 0) + a.wealth;
  }
  const maxWealth = Math.max(1, ...FACTIONS.map((f) => wealth[f.key] || 0));
  const openBiz = businesses.filter((b) => b.status === "open").length;
  const failedBiz = businesses.filter((b) => b.status === "bankrupt").length;

  return (
    <aside style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card card-pad">
        <div className="card-title">Factions</div>
        <div className="filters">
          {FACTIONS.map((f) => (
            <div
              key={f.key}
              className={`filter-chip ${factionFilter === f.key ? "active" : ""}`}
              onClick={() => onFilter(factionFilter === f.key ? null : f.key)}
            >
              <span className="dot" style={{ background: f.color }} />
              {f.label}
              <span className="cnt">{counts[f.key] || 0}</span>
            </div>
          ))}
        </div>
        {factionFilter && (
          <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
            Filtering · click again to clear
          </div>
        )}
      </div>

      <div className="card card-pad">
        <div className="card-title">Wealth by faction</div>
        <div className="minibars">
          {FACTIONS.map((f) => (
            <div key={f.key} className="minibar">
              <div className="ml">
                <span>{f.label}</span>
                <span className="num">₹{Math.round(wealth[f.key] || 0).toLocaleString()}</span>
              </div>
              <div className="mt">
                <i style={{ width: `${((wealth[f.key] || 0) / maxWealth) * 100}%`, background: f.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card card-pad">
        <div className="card-title">Economy</div>
        <div className="minibars" style={{ gap: 6 }}>
          <div className="rel-row"><span>Active firms</span><span className="num" style={{ color: "var(--warn)" }}>{openBiz}</span></div>
          <div className="rel-row"><span>Bankrupt</span><span className="num" style={{ color: "var(--bad)" }}>{failedBiz}</span></div>
        </div>
      </div>
    </aside>
  );
}
