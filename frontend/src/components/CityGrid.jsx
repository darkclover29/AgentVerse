import { useState } from "react";

const OCCUPATION_LABEL = {
  executive: "Corporator / Neta",
  analyst: "Bureaucrat / Clerk",
  engineer: "Traffic Commissioner",
  clerk: "RTO Inspector",
  netrunner: "IT Project Manager",
  fixer: "Jugaad Coder / Freelancer",
  "data-broker": "Moonlighting Developer",
  courier: "Blinkit Delivery Agent",
  enforcer: "Auto Union President",
  smuggler: "Water Tanker Operator",
  dealer: "Black Ticket Seller",
  lieutenant: "Local Gang Leader",
  drifter: "UPSC Aspirant / Student",
  mechanic: "Rickshaw Mechanic",
  medic: "Government Pharmacist",
  vendor: "Chai Tapri Owner",
  unemployed: "Unemployed Graduate",
};

function tileType(map, x, y) {
  return map[`${x},${y}`] || "hab_block";
}

const MICRO_ICONS = {
  hab_block: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  ),
  corp_tower: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="9" y1="22" x2="9" y2="2" />
      <line x1="15" y1="22" x2="15" y2="2" />
      <line x1="4" y1="8" x2="20" y2="8" />
      <line x1="4" y1="14" x2="20" y2="14" />
    </svg>
  ),
  market_node: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 0 1-8 0" />
    </svg>
  ),
  net_cafe: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  enforcer_post: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  plaza: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.0" className="tile-icon">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="16" />
      <line x1="8" y1="12" x2="16" y2="12" />
    </svg>
  )
};

export default function CityGrid({
  tiles, gridSize, agents, businesses = [], onSelect,
  selectedId = null, factionFilter = null, overlayMode = "none",
  editMode = false, onTileUpdate
}) {
  const [editingTile, setEditingTile] = useState(null);
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!tiles.length) return <div className="muted">Loading city…</div>;

  const map = {};
  for (const t of tiles) map[`${t.x},${t.y}`] = t.type;

  // Pre-calculate cell wealth and faction metrics for overlays
  const cellWealth = {};
  const cellFactionCount = {};
  
  for (const a of agents) {
    const key = `${a.x},${a.y}`;
    cellWealth[key] = (cellWealth[key] || 0) + a.wealth;
    if (!cellFactionCount[key]) cellFactionCount[key] = {};
    cellFactionCount[key][a.faction] = (cellFactionCount[key][a.faction] || 0) + 1;
  }
  for (const b of businesses) {
    if (b.status === "open") {
      const key = `${b.x},${b.y}`;
      cellWealth[key] = (cellWealth[key] || 0) + b.capital;
      const owner = agents.find(a => a.id === b.owner_id);
      const fact = owner ? owner.faction : "unaligned";
      if (!cellFactionCount[key]) cellFactionCount[key] = {};
      cellFactionCount[key][fact] = (cellFactionCount[key][fact] || 0) + 2; // weight business heavier
    }
  }

  const getCellWealth = (x, y) => cellWealth[`${x},${y}`] || 0;
  const getCellFaction = (x, y) => {
    const counts = cellFactionCount[`${x},${y}`];
    if (!counts) return null;
    let maxFact = null, maxCount = 0;
    for (const [f, c] of Object.entries(counts)) {
      if (c > maxCount) { maxCount = c; maxFact = f; }
    }
    return maxFact;
  };

  const cells = [];
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const cellStyle = {};
      if (overlayMode === "wealth") {
        const w = getCellWealth(x, y);
        if (w > 0) {
          cellStyle.background = `rgba(245, 158, 11, ${Math.min(0.65, w / 400)})`;
          cellStyle.boxShadow = "inset 0 0 5px rgba(245, 158, 11, 0.4)";
        }
      } else if (overlayMode === "faction") {
        const fact = getCellFaction(x, y);
        if (fact) {
          const colors = { corp: "74, 158, 255", hacker: "176, 124, 240", syndicate: "240, 113, 106", unaligned: "125, 135, 153" };
          cellStyle.background = `rgba(${colors[fact]}, 0.22)`;
          cellStyle.boxShadow = `inset 0 0 5px rgba(${colors[fact]}, 0.5)`;
        }
      }

      const type = tileType(map, x, y);
      cells.push(
        <div 
          key={`${x},${y}`} 
          className={`tile ${type} ${editMode ? "editable-tile" : ""}`}
          style={cellStyle}
          onClick={() => {
            if (editMode) {
              setEditingTile({ x, y, current: type });
            }
          }}
          onMouseEnter={() => setHoveredCell({ x, y })}
          onMouseLeave={() => setHoveredCell(null)}
        >
          <div className="tile-glow-border"></div>
          {MICRO_ICONS[type]}
        </div>
      );
    }
  }

  const pct = (n) => `${((n + 0.5) / gridSize) * 100}%`;
  const selectedAgent = agents.find(a => a.id === selectedId);

  return (
    <div className="grid-wrap">
      {hoveredCell && (
        <div className="grid-telemetry-hud font-mono">
          <div className="hud-line"><span className="label">LOC:</span> <span className="val">[{hoveredCell.x.toString().padStart(2, "0")}, {hoveredCell.y.toString().padStart(2, "0")}]</span></div>
          <div className="hud-line"><span className="label">NODE:</span> <span className="val">{map[`${hoveredCell.x},${hoveredCell.y}`]?.toUpperCase().replace("_", " ")}</span></div>
          {(() => {
            const b = businesses.find(x => x.x === hoveredCell.x && x.y === hoveredCell.y && x.status === "open");
            return b ? (
              <div className="hud-line"><span className="label">BIZ:</span> <span className="val">{b.name.toUpperCase()} (₹{Math.round(b.capital)})</span></div>
            ) : null;
          })()}
          {(() => {
            const cellAgents = agents.filter(a => a.x === hoveredCell.x && a.y === hoveredCell.y);
            return cellAgents.length > 0 ? (
              <div className="hud-line"><span className="label">UNIT:</span> <span className="val">{cellAgents.map(a => a.name.split(" ")[0].toUpperCase()).join(", ")}</span></div>
            ) : null;
          })()}
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: `repeat(${gridSize}, 1fr)` }}>
        {cells}
      </div>
      <div className="overlay">
        {/* Draw SVG Pathing Line */}
        {selectedAgent && selectedAgent.dest_x !== undefined && selectedAgent.dest_y !== undefined && (
          <svg className="path-svg" viewBox={`0 0 ${gridSize} ${gridSize}`} style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 5 }}>
            <line
              x1={selectedAgent.x + 0.5}
              y1={selectedAgent.y + 0.5}
              x2={selectedAgent.dest_x + 0.5}
              y2={selectedAgent.dest_y + 0.5}
              stroke="var(--accent)"
              strokeWidth="0.1"
              strokeDasharray="0.15 0.1"
              strokeLinecap="round"
            />
            <circle cx={selectedAgent.dest_x + 0.5} cy={selectedAgent.dest_y + 0.5} r="0.15" fill="var(--accent)" />
          </svg>
        )}

        {businesses.filter((b) => b.status === "open").map((b) => (
          <div key={`b${b.id}`} className="biz" title={`${b.name} · ₹${Math.round(b.capital)}`}
               style={{ left: pct(b.x), top: pct(b.y) }} />
        ))}
        {agents.map((a) => {
          const dim = factionFilter && a.faction !== factionFilter;
          const sel = a.id === selectedId;
          return (
            <button
              key={a.id}
              className={`adot ${a.faction}${a.tier === 2 ? " t2" : ""}${dim ? " dim" : ""}${sel ? " sel" : ""}`}
              title={`${a.name} · ${OCCUPATION_LABEL[a.occupation] || a.occupation}${a.tier === 2 ? " · LLM" : ""}`}
              style={{ left: pct(a.x), top: pct(a.y) }}
              onClick={() => onSelect && onSelect(a)}
            />
          );
        })}
      </div>

      {editingTile && (
        <div className="tile-editor-popup">
          <h4>Change Tile ({editingTile.x}, {editingTile.y})</h4>
          <select
            value={editingTile.current}
            onChange={(e) => {
              if (onTileUpdate) onTileUpdate(editingTile.x, editingTile.y, e.target.value);
              setEditingTile(null);
            }}
          >
            <option value="hab_block">Chawl / Colony (Housing)</option>
            <option value="corp_tower">IT Park / Tech Tower (Office)</option>
            <option value="market_node">Kirana / Bazar Shop (Market)</option>
            <option value="net_cafe">Internet Cafe / Cyber Tapri</option>
            <option value="enforcer_post">Police Chowki / Post (Security)</option>
            <option value="plaza">Maidan / Public Park (Leisure)</option>
          </select>
          <button onClick={() => setEditingTile(null)}>Close</button>
        </div>
      )}
    </div>
  );
}
