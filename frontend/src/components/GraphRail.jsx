// Right rail for the Network view: edge-type toggles, legend, and live graph stats
// (alliance/rivalry counts, most-connected agent, faction with the most ties).

export default function GraphRail({ data, showFriend, showRival, onToggle, onSelect }) {
  const friend = data.edges.filter((e) => e.kind === "friendship").length;
  const rival = data.edges.filter((e) => e.kind === "rivalry").length;

  const deg = {};
  for (const e of data.edges) {
    deg[e.source] = (deg[e.source] || 0) + 1;
    deg[e.target] = (deg[e.target] || 0) + 1;
  }
  const byId = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
  const top = Object.entries(deg)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([id, d]) => ({ node: byId[Number(id)] || byId[id], d }))
    .filter((t) => t.node);

  return (
    <aside style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card card-pad">
        <div className="card-title">Edges</div>
        <div className="filters">
          <div className={`filter-chip ${showFriend ? "active" : ""}`} onClick={() => onToggle("friend")}>
            <span className="dot" style={{ background: "var(--good)" }} />
            Friendships
            <span className="cnt">{friend}</span>
          </div>
          <div className={`filter-chip ${showRival ? "active" : ""}`} onClick={() => onToggle("rival")}>
            <span className="dot" style={{ background: "var(--bad)" }} />
            Rivalries
            <span className="cnt">{rival}</span>
          </div>
        </div>
        <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
          Click a node to inspect · drag to reposition
        </div>
      </div>

      <div className="card card-pad">
        <div className="card-title">Most connected</div>
        {top.length ? top.map((t) => (
          <div key={t.node.id} className="rel-row" style={{ cursor: "pointer" }}
               onClick={() => onSelect && onSelect(t.node.id)}>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="fdot" style={{ background: factionColor(t.node.faction) }} />
              {t.node.name}
            </span>
            <span className="num" style={{ color: "var(--text-3)" }}>{t.d}</span>
          </div>
        )) : <div className="muted">Run the sim to form ties.</div>}
      </div>
    </aside>
  );
}

function factionColor(f) {
  return { corp: "var(--corp)", hacker: "var(--hacker)", syndicate: "var(--syndicate)", unaligned: "var(--unaligned)" }[f] || "var(--unaligned)";
}
