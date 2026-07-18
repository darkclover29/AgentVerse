import { useEffect, useRef, useState } from "react";
import CityGrid from "./components/CityGrid.jsx";
import CityRail from "./components/CityRail.jsx";
import NewsFeed from "./components/NewsFeed.jsx";
import Timeline from "./components/Timeline.jsx";
import RelationshipGraph from "./components/RelationshipGraph.jsx";
import GraphRail from "./components/GraphRail.jsx";
import AgentPanel from "./components/AgentPanel.jsx";
import AgentDossierModal from "./components/AgentDossierModal.jsx";
import FactionCharts from "./components/FactionCharts.jsx";
import Newspaper from "./components/Newspaper.jsx";
import * as Icon from "./components/Icons.jsx";
import * as api from "./api.js";

const FACTION_COLOR = {
  corp: "var(--corp)", hacker: "var(--hacker)",
  syndicate: "var(--syndicate)", unaligned: "var(--unaligned)",
};

export default function App() {
  const [world, setWorld] = useState({ tiles: [], grid_size: 20 });
  const [agents, setAgents] = useState([]);
  const [clock, setClock] = useState({ day: 0, tick: 0 });
  const [news, setNews] = useState(null);
  const [running, setRunning] = useState(false);
  const [viewDay, setViewDay] = useState(0);
  const [view, setView] = useState("city");
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState(null);
  const [businesses, setBusinesses] = useState([]);
  const [factionFilter, setFactionFilter] = useState(null);
  const [search, setSearch] = useState("");
  const [edgeToggles, setEdgeToggles] = useState({ friend: true, rival: true });
  const [overlayMode, setOverlayMode] = useState("none");
  const [editMode, setEditMode] = useState(false);
  const [gdpHistory, setGdpHistory] = useState([]);
  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState("all");
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [showDossierModal, setShowDossierModal] = useState(false);
  const [environment, setEnvironment] = useState(null);
  const sockRef = useRef(null);

  function selectById(id) {
    const a = agents.find((x) => x.id === id);
    if (a) setSelected(a);
  }

  async function loadGraph() { setGraph(await api.getGraph()); }

  useEffect(() => {
    api.getWorld().then(setWorld);
    api.getAgents().then(setAgents);
    api.getClock().then((c) => { setClock(c); setViewDay(c.day); });
    api.getStatus().then(setStatus);
    api.getBusinesses().then(setBusinesses);
  }, []);

  useEffect(() => { api.getBusinesses().then(setBusinesses); }, [clock.day]);

  useEffect(() => {
    api.getEnvironment(viewDay, viewDay === clock.day ? clock.tick : 12).then(setEnvironment);
  }, [viewDay, clock.tick, clock.day]);

  const selectedLive = selected
    ? agents.find((a) => a.id === selected.id) || selected
    : null;

  useEffect(() => { api.getNews(viewDay).then(setNews); }, [viewDay]);
  useEffect(() => { if (view === "network") loadGraph(); }, [view]);

  // Recalculate GDP History when clock day changes
  useEffect(() => {
    if (clock.day === 0 && gdpHistory.length > 0) {
      setGdpHistory([]);
    }
    if (agents.length > 0) {
      const currentGdp = Math.round(agents.reduce((s, a) => s + a.wealth, 0) + businesses.filter(b => b.status === "open").reduce((s, b) => s + b.capital, 0));
      setGdpHistory((prev) => {
        if (prev.some(d => d.day === clock.day)) return prev;
        return [...prev, { day: clock.day, gdp: currentGdp }].slice(-30);
      });
    }
  }, [clock.day, agents.length]);

  useEffect(() => {
    if (!running) { sockRef.current?.close(); sockRef.current = null; return; }
    const sock = api.openSocket((msg) => {
      setClock({ day: msg.day, tick: msg.tick, kitty_pool: msg.kitty_pool });
      setViewDay(msg.day);
      setAgents((prev) => prev.map((a) => {
        const u = msg.agents.find((m) => m.id === a.id);
        return u ? { ...a, x: u.x, y: u.y, wealth: u.wealth } : a;
      }));
      
      // Live logging of WebSocket streamed events
      if (msg.events && msg.events.length > 0) {
        setLogs((prev) => {
          const names = Object.fromEntries(agents.map(a => [a.id, a.name]));
          const factions = Object.fromEntries(agents.map(a => [a.id, a.faction]));
          
          const newLogs = msg.events.map(e => {
            const time = `${String(e.tick).padStart(2, "0")}:00`;
            const actor = names[e.agent_id] || `Agent ${e.agent_id}`;
            const target = names[e.target_id] || "";
            const p = e.payload || {};
            let text = "";
            
            if (e.type === "found_business") {
              text = `${actor} opened ${p.name || "business"}.`;
            } else if (e.type === "hire") {
              text = `${actor} hired ${target} at ${p.business || "venture"}.`;
            } else if (e.type === "revenue") {
              text = `${p.business} generated ₹${p.net} net revenue.`;
            } else if (e.type === "bankrupt") {
              text = `⚠️ ${p.business} went bankrupt!`;
            } else if (e.type === "consume") {
              text = `${actor} spent ₹${p.amount} on ${p.need === "energy" ? "Adrak Chai" : "Chai & Snacks"}.`;
            } else if (e.type === "betray") {
              text = `⚔️ ${actor} betrayed ${target}!`;
            } else if (e.type === "help") {
              text = `🤝 ${actor} helped ${target}.`;
            } else if (e.type === "data_heist") {
              text = `💾 Moonlighter ${actor} siphoned ₹${p.amount} from ${p.business_name}.`;
            } else if (e.type === "shakedown") {
              text = `💸 Auto Union ${actor} extorted ₹${p.amount} from ${p.business_name}.`;
            } else if (e.type === "lockdown") {
              text = `🚨 Authority ${actor} fined ${p.business_name} ₹${p.amount}.`;
            } else if (e.type === "mutual_aid") {
              text = `✊ Mohalla Committee pooled ₹${p.amount} for ${p.business_name}.`;
            } else if (e.type === "chat") {
              const firstLine = p.dialogue && p.dialogue[0] ? p.dialogue[0].text : "";
              text = `💬 ${actor} spoke with ${target}: "${firstLine.substring(0, 40)}..."`;
            } else {
              text = `${actor} performed: ${e.type}.`;
            }
            
            // Faction attribution
            const bizOwner = businesses.find(b => b.name === p.business || b.name === p.business_name)?.owner_id;
            const faction = factions[e.agent_id] || (bizOwner ? factions[bizOwner] : "unaligned");

            // Category classification
            let category = "social";
            if (["betray", "data_heist", "shakedown", "lockdown"].includes(e.type)) {
              category = "security";
            } else if (["found_business", "revenue", "bankrupt", "consume", "mutual_aid"].includes(e.type)) {
              category = "financial";
            }
            
            return { id: e.id, day: e.day, tick: e.tick, time, text, faction, category };
          });
          return [...prev, ...newLogs].slice(-100);
        });
      }
    });
    sockRef.current = sock;
    return () => sock.close();
  }, [running, agents.length]);

  // Client-side simulation ticker for static mode
  useEffect(() => {
    if (!running || !api.isStatic()) return;

    const interval = setInterval(async () => {
      const c = await api.step(1);
      api.setStaticClock(c.day, c.tick);
      setClock(c);
      setViewDay(c.day);
      
      const activeAgents = await api.getAgents();
      setAgents(activeAgents);
      
      const biz = await api.getBusinesses();
      setBusinesses(biz);
      
      const env = await api.getEnvironment(c.day, c.tick);
      setEnvironment(env);
      
      const staticLogs = api.getStaticLogs();
      setLogs(staticLogs);
      
      if (c.day === 30 && c.tick === 23) {
        setRunning(false);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [running]);

  async function manualStep(ticks) {
    const c = await api.step(ticks);
    if (api.isStatic()) {
      api.setStaticClock(c.day, c.tick);
      setClock(c);
      setViewDay(c.day);
      setAgents(await api.getAgents());
      setBusinesses(await api.getBusinesses());
      setEnvironment(await api.getEnvironment(c.day, c.tick));
      setLogs(api.getStaticLogs());
    } else {
      setClock(c); setViewDay(c.day);
      setAgents(await api.getAgents());
    }
  }

  async function scrub(day) {
    setViewDay(day);
    if (api.isStatic()) {
      api.setStaticClock(day, 23);
      setClock({ day: day, tick: 23 });
      setAgents(await api.getAgents());
      setBusinesses(await api.getBusinesses());
      setEnvironment(await api.getEnvironment(day, 23));
      setLogs(api.getStaticLogs());
    } else {
      const snap = await api.getReplay(day);
      setAgents((prev) => prev.map((a) => {
        const s = snap.agents.find((m) => m.id === a.id);
        return s ? { ...a, x: s.x, y: s.y, wealth: s.wealth } : a;
      }));
    }
  }

  const t2count = agents.filter((a) => a.tier === 2).length;
  const totalWealth = Math.round(agents.reduce((s, a) => s + a.wealth, 0));
  const openBiz = businesses.filter((b) => b.status === "open").length;

  const listAgents = [...agents]
    .filter((a) => !factionFilter || a.faction === factionFilter)
    .filter((a) => !search || a.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => (b.tier - a.tier) || (b.wealth - a.wealth))
    .slice(0, 40);

  return (
    <div className="app">
      <div className="main">
        <header className="hud">
          <div>
            <div className="brand">AGENT<b>VERSE</b></div>
            <div className="sub">Chaotic Indian Metropolis · {agents.length} side-hustlers & citizens</div>
          </div>
          {status && (
            <span className="badge" title="Tier-2 planning backend">
              <span className={`led ${status.ollama ? "" : "off"}`} />
              {status.ollama ? status.model : "heuristic planner"}
            </span>
          )}
          <div className="hud-stats">
            <div className="stat"><span className="k">Day</span><span className="v accent">{clock.day}</span></div>
            <div className="stat"><span className="k">Time</span><span className="v">{String(clock.tick).padStart(2, "0")}:00</span></div>
            <div className="stat"><span className="k">Firms</span><span className="v">{openBiz}</span></div>
            <div className="stat"><span className="k">Wealth</span><span className="v">₹{totalWealth.toLocaleString()}</span></div>
          </div>
        </header>

        <div className="content">
          <div className="toolbar">
            <div className="tabs">
              <button className={`tab ${view === "city" ? "active" : ""}`} onClick={() => setView("city")}>
                <Icon.City /> City
              </button>
              <button className={`tab ${view === "charts" ? "active" : ""}`} onClick={() => setView("charts")}>
                <Icon.Network /> Charts
              </button>
              <button className={`tab ${view === "newspaper" ? "active" : ""}`} onClick={() => setView("newspaper")}>
                <Icon.Newspaper /> Newspaper
              </button>
              <button className={`tab ${view === "network" ? "active" : ""}`} onClick={() => setView("network")}>
                <Icon.Network /> Network
              </button>
            </div>
            <div className="controls">
              <button className="primary" onClick={() => setRunning((r) => !r)}>
                {running ? <Icon.Pause /> : <Icon.Play />} {running ? "Pause" : "Run"}
              </button>
              <button onClick={() => manualStep(1)} disabled={running}><Icon.StepForward /> Hour</button>
              <button onClick={() => manualStep(24)} disabled={running}><Icon.FastForward /> Day</button>
              
              {view === "city" && (
                <>
                  <select value={overlayMode} onChange={(e) => setOverlayMode(e.target.value)} className="overlay-select">
                    <option value="none">No Overlay</option>
                    <option value="wealth">Wealth Heatmap</option>
                    <option value="faction">Faction Territory</option>
                  </select>
                  <button className={editMode ? "active-btn" : ""} onClick={() => setEditMode(!editMode)}>
                    {editMode ? "✍ Editing" : "✍ Edit Map"}
                  </button>
                </>
              )}
              
              <button onClick={async () => {
                await api.reproject();
                setAgents(await api.getAgents());
                setBusinesses(await api.getBusinesses());
              }} title="Rebuild database projections from event log"><Icon.Refresh /> Reproject</button>

              <button onClick={async () => {
                await api.reset(); 
                if (api.isStatic()) {
                  api.setStaticClock(0, 0);
                  setClock({ day: 0, tick: 0, kitty_pool: 100 }); 
                  setViewDay(0);
                  setSelected(null); 
                  setAgents(await api.getAgents());
                  setBusinesses(await api.getBusinesses());
                  setLogs(api.getStaticLogs());
                  setEnvironment(await api.getEnvironment(0, 0));
                } else {
                  setClock({ day: 0, tick: 0 }); setViewDay(0);
                  setSelected(null); setAgents(await api.getAgents());
                  setBusinesses(await api.getBusinesses());
                }
              }}><Icon.Reset /> Reset</button>
              {view === "network" && (
                <button onClick={loadGraph}><Icon.Refresh /> Refresh</button>
              )}
            </div>
          </div>

          {view === "city" ? (
            <>
              <div className="city">
                <div>
                  <CityGrid
                    tiles={world.tiles} gridSize={world.grid_size} agents={agents}
                    businesses={businesses} onSelect={setSelected}
                    selectedId={selectedLive?.id} factionFilter={factionFilter}
                    overlayMode={overlayMode} editMode={editMode}
                    environment={environment}
                    onTileUpdate={async (x, y, type) => {
                      await api.updateTile(x, y, type);
                      setWorld(await api.getWorld());
                    }}
                  />
                  <Timeline day={viewDay} maxDay={api.isStatic() ? 30 : clock.day} onScrub={scrub} />
                </div>
                <CityRail
                  agents={agents} businesses={businesses}
                  factionFilter={factionFilter} onFilter={setFactionFilter}
                />
              </div>
            </>
          ) : view === "charts" ? (
            <div style={{ width: "100%", marginTop: 10 }}>
              <FactionCharts agents={agents} businesses={businesses} gdpHistory={gdpHistory} />
            </div>
          ) : view === "newspaper" ? (
            <div style={{ width: "100%", marginTop: 10 }}>
              <Newspaper day={viewDay} />
            </div>
          ) : (
            <div className="city">
              <div className="card" style={{ padding: 4 }}>
                <RelationshipGraph
                  key={graph.edges.length} data={graph}
                  onSelect={selectById} selectedId={selectedLive?.id}
                  showFriend={edgeToggles.friend} showRival={edgeToggles.rival}
                />
              </div>
              <GraphRail
                data={graph} showFriend={edgeToggles.friend} showRival={edgeToggles.rival}
                onToggle={(k) => setEdgeToggles((t) => ({ ...t, [k]: !t[k] }))}
                onSelect={selectById}
              />
            </div>
          )}
        </div>

        {/* Terminal Log Console */}
        <div className={`drawer glass ${drawerOpen ? "open" : "collapsed"}`}>
          <div className="drawer-header" onClick={() => setDrawerOpen(!drawerOpen)}>
            <div className="title">
              <span className="blink">■</span> METROPOLITAN LOG CONSOLE (TERMINAL_LOG)
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span className="live-signal font-mono">
                <span className="led-green"></span> LIVE_TELEMETRY
              </span>
              <button className="toggle-btn" onClick={(e) => { e.stopPropagation(); setDrawerOpen(!drawerOpen); }}>
                {drawerOpen ? "▼ Collapse" : "▲ Expand"}
              </button>
            </div>
          </div>
          {drawerOpen && (
            <>
              <div className="drawer-filters">
                <button className={`filter-btn ${logFilter === "all" ? "active" : ""}`} onClick={() => setLogFilter("all")}>ALL</button>
                <button className={`filter-btn ${logFilter === "security" ? "active" : ""}`} onClick={() => setLogFilter("security")}>SECURITY</button>
                <button className={`filter-btn ${logFilter === "financial" ? "active" : ""}`} onClick={() => setLogFilter("financial")}>FINANCIAL</button>
                <button className={`filter-btn ${logFilter === "social" ? "active" : ""}`} onClick={() => setLogFilter("social")}>SOCIAL</button>
              </div>
              <div className="drawer-content scrollable">
                {logs
                  .filter((log) => logFilter === "all" || log.category === logFilter)
                  .map((log, i) => (
                    <div key={`${log.id}-${i}`} className={`log-line faction-${log.faction || "unaligned"}`}>
                      <span className="time">Day {log.day} · {log.time}</span>
                      <span className="separator">&gt;&gt;</span>
                      <span className="msg">{log.text}</span>
                    </div>
                  ))}
                {logs.filter((log) => logFilter === "all" || log.category === logFilter).length === 0 && (
                  <div className="muted font-mono" style={{ fontSize: 11, padding: "10px 0" }}>NO LOG PACKETS IN THIS NODE.</div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <aside className="sidebar">
        {selectedLive ? (
          <AgentPanel agent={selectedLive} onClose={() => setSelected(null)} onInspect={() => setShowDossierModal(true)} />
        ) : (
          <>
            <div className="section-title">Environmental Sensors</div>
            <div className="card card-pad sensor-widget font-mono" style={{ marginBottom: "15px" }}>
              <div className="sensor-row">
                <span className="lbl">WEATHER:</span>
                <span className={`val sensor-badge ${environment?.is_monsoon ? "poor" : "good"}`}>
                  {environment?.is_monsoon ? "MONSOON FLOOD" : "CLEAR SKY"}
                </span>
              </div>
              <div className="sensor-row">
                <span className="lbl">AQI INDEX:</span>
                <span className={`val sensor-badge ${
                  (environment?.aqi_level || 0) < 150 ? "good" : (environment?.aqi_level || 0) < 250 ? "moderate" : "poor"
                }`}>
                  {environment?.aqi_level || 100} ({environment?.aqi_status || "GOOD"})
                </span>
              </div>
              <div className="sensor-row">
                <span className="lbl">TRAFFIC:</span>
                <span className={`val sensor-badge ${environment?.is_traffic_gridlock ? "poor" : "good"}`}>
                  {environment?.is_traffic_gridlock ? "SILK BOARD BLOCKED" : "NORMAL LANES"}
                </span>
              </div>
              <div className="sensor-row">
                <span className="lbl">KITTY POOL:</span>
                <span className="val" style={{ color: "#10b981", fontWeight: "bold" }}>
                  ₹{Math.round(clock.kitty_pool || 100)}
                </span>
              </div>
            </div>

            <div className="section-title">City Feed · Day {news?.day ?? 0}</div>
            <NewsFeed news={news} />

            <div className="section-title">Agents</div>
            <div className="search">
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                     placeholder="Search agents…" />
            </div>
            {listAgents.map((a) => (
              <div key={a.id} className={`agent-row ${selectedLive?.id === a.id ? "sel" : ""}`}
                   onClick={() => setSelected(a)}>
                <span className="fdot" style={{ background: FACTION_COLOR[a.faction] }} />
                <span className="nm">{a.tier === 2 ? <span className="star">★ </span> : ""}{a.name}</span>
                <span className="meta">₹{Math.round(a.wealth)}</span>
              </div>
            ))}
            {listAgents.length === 0 && <div className="muted">No agents match.</div>}
          </>
        )}
      </aside>
      {showDossierModal && selectedLive && (
        <AgentDossierModal agent={selectedLive} onClose={() => setShowDossierModal(false)} />
      )}
    </div>
  );
}
