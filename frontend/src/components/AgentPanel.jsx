import { useEffect, useState } from "react";
import * as api from "../api.js";
import * as Icon from "./Icons.jsx";
import Sparkline from "./Sparkline.jsx";

const FACTION_COLOR = {
  corp: "var(--corp)", hacker: "var(--hacker)",
  syndicate: "var(--syndicate)", unaligned: "var(--unaligned)",
};

const FACTION_LABEL = {
  corp: "Authority & Netas",
  hacker: "IT & Side-Hustlers",
  syndicate: "Auto & Cab Cartels",
  unaligned: "Vendors & Citizens",
};

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

function statColor(v) {
  if (v >= 60) return "var(--good)";
  if (v >= 30) return "var(--warn)";
  return "var(--bad)";
}

export default function AgentPanel({ agent, onClose, onInspect }) {
  const [plan, setPlan] = useState(null);
  const [memories, setMemories] = useState([]);
  const [rels, setRels] = useState([]);
  const [history, setHistory] = useState([]);
  const [chats, setChats] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sublinkHistory, setSublinkHistory] = useState([]);
  const [userMsg, setUserMsg] = useState("");
  const [sublinkLoading, setSublinkLoading] = useState(false);
  const [tab, setTab] = useState("stats");

  useEffect(() => {
    setSublinkHistory([]);
    setUserMsg("");
    setSublinkLoading(false);
  }, [agent?.id]);

  useEffect(() => {
    if (!agent) return;
    api.getPlan(agent.id).then(setPlan);
    api.getMemories(agent.id).then((d) => setMemories(d.memories || []));
    api.getRelationships(agent.id).then((d) => setRels(d.relationships || []));
    api.getHistory(agent.id).then((d) => setHistory(d.series || []));
    api.getAgentChats(agent.id).then((d) => setChats(d.chats || []));
    api.getAgentTimeline(agent.id).then(setTimeline);
  }, [agent]);

  if (!agent) return null;

  return (
    <div className="panel">
      <div className="panel-head">
        <strong>{agent.name}</strong>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {onInspect && (
            <button 
              className="btn font-mono" 
              onClick={onInspect} 
              style={{ fontSize: 9.5, padding: "3px 8px", background: "var(--accent-soft)", color: "var(--accent)", borderColor: "rgba(52, 208, 191, 0.3)", cursor: "pointer" }}
              title="Open full tactical Operations HUD"
            >
              👁️ HUD
            </button>
          )}
          <button className="x" onClick={onClose} aria-label="Close"><Icon.Close /></button>
        </div>
      </div>

      <div className="panel-meta">
        <span className="chip">
          <span className="dot" style={{ background: FACTION_COLOR[agent.faction] }} />
          {FACTION_LABEL[agent.faction] || agent.faction}
        </span>
        <span>{OCCUPATION_LABEL[agent.occupation] || agent.occupation}</span>
        <span className="muted">{agent.tier === 2 ? "★ Tier-2 Planner" : "Tier-1"}</span>
      </div>

      {/* Biometric Avatar HUD */}
      <div className="biometric-avatar">
        <svg viewBox="0 0 100 100" className="bio-svg">
          <circle cx="50" cy="50" r="45" stroke="rgba(52, 208, 191, 0.08)" strokeWidth="1" fill="none" />
          <circle cx="50" cy="50" r="38" stroke="rgba(52, 208, 191, 0.15)" strokeWidth="1.5" strokeDasharray="5 5" fill="none" className="rot-cw" />
          <circle cx="50" cy="50" r="30" stroke="var(--accent)" strokeWidth="1" strokeDasharray="40 180" fill="none" className="rot-ccw" />
          <path d="M50 15 L50 85 M15 50 L85 50" stroke="rgba(52, 208, 191, 0.12)" strokeWidth="0.5" />
          <path d="M 40,40 L 40,35 L 45,35" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M 60,40 L 60,35 L 55,35" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M 40,60 L 40,65 L 45,65" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M 60,60 L 60,65 L 55,65" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M38,45 Q42,32 50,32 Q58,32 62,45 Q64,55 58,68 Q50,75 42,68 Q36,55 38,45 Z" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1" fill="none" />
          <ellipse cx="44" cy="45" rx="3" ry="1.5" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <ellipse cx="56" cy="45" rx="3" ry="1.5" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M47,53 Q50,56 53,53" stroke="var(--accent)" strokeWidth="1" fill="none" />
          <path d="M45,60 Q50,64 55,60" stroke="rgba(255,255,255,0.4)" strokeWidth="1" fill="none" />
        </svg>
        <div className="bio-telemetry font-mono">
          <div>ID_REF: {agent.id.toString().padStart(4, "0")}</div>
          <div>STATUS: ACTIVE</div>
          <div>COGNITIVE: {agent.tier === 2 ? "SECURE" : "HEURISTIC"}</div>
        </div>
      </div>

      <div className="panel-tabs" style={{ display: "flex", gap: 10, flexWrap: "wrap", borderBottom: "1px solid var(--border)", paddingBottom: 6, marginBottom: 12 }}>
        <button className={`tab-btn ${tab === "stats" ? "active" : ""}`} onClick={() => setTab("stats")}>Bio & Stats</button>
        <button className={`tab-btn ${tab === "brain" ? "active" : ""}`} onClick={() => setTab("brain")}>Brain</button>
        <button className={`tab-btn ${tab === "sublink" ? "active" : ""}`} onClick={() => setTab("sublink")}>Sublink (Direct Chat)</button>
        <button className={`tab-btn ${tab === "chats" ? "active" : ""}`} onClick={() => setTab("chats")}>Chats ({chats.length})</button>
      </div>

      {tab === "stats" && (
        <>
          <div className="bars">
            <div className="bar-row">
              <span className="lbl">Wealth</span>
              <span className="bar"><i style={{ width: `${Math.min(100, agent.wealth / 10)}%`, background: "var(--accent)" }} /></span>
              <span className="num">₹{Math.round(agent.wealth)}</span>
            </div>
            <div className={`bar-row ${agent.happiness < 30 ? "critical-stat" : ""}`}>
              <span className="lbl">Mood (Chai/Relief)</span>
              <span className="bar"><i style={{ width: `${agent.happiness}%`, background: statColor(agent.happiness) }} /></span>
              <span className="num">
                {agent.happiness < 30 && <span className="warning-blink">⚠️ </span>}
                {Math.round(agent.happiness)}
              </span>
            </div>
            <div className={`bar-row ${agent.energy < 30 ? "critical-stat" : ""}`}>
              <span className="lbl">Energy (Chai)</span>
              <span className="bar"><i style={{ width: `${agent.energy}%`, background: statColor(agent.energy) }} /></span>
              <span className="num">
                {agent.energy < 30 && <span className="warning-blink">⚠️ </span>}
                {Math.round(agent.energy)}
              </span>
            </div>
          </div>

          <div className="section-title">Trends</div>
          <Sparkline series={history} accessor={(d) => d.wealth} color="var(--accent)" label="Wealth" unit="₹" />
          <Sparkline series={history} accessor={(d) => d.happiness} color="var(--good)" label="Happiness" />

          <div className="section-title">Relationships</div>
          {rels.length ? rels.map((r) => (
            <div key={r.id} className="rel-row">
              <span>{r.name}</span>
              <span className={`rel-strength ${r.friendship > r.rivalry ? "friend" : "rival"}`}>
                {r.friendship > r.rivalry
                  ? `+${Math.round(r.friendship)} ally`
                  : `−${Math.round(r.rivalry)} rival`}
              </span>
            </div>
          )) : <div className="muted">No relationships yet.</div>}
        </>
      )}

      {tab === "brain" && (
        <>
          {agent.tier === 2 && (
            <>
              <div className="section-title">Current Plan</div>
              {plan?.goal ? (
                <>
                  <div className="goal">
                    <Icon.Target width={15} height={15} />
                    <span>{plan.goal}
                      <span className="muted"> · {plan.source === "llm" ? "LLM" : "heuristic"}</span>
                    </span>
                  </div>
                  <ol className="steps">
                    {(plan.steps || []).map((s, i) => (
                      <li key={i} className={i < plan.step_index ? "done" : ""}>
                        {s.action}{s.note ? ` — ${s.note}` : ""}
                      </li>
                    ))}
                  </ol>
                </>
              ) : <div className="muted">No active plan yet — run the sim.</div>}
            </>
          )}

          <div className="section-title">Memory & Event Timeline</div>
          {timeline.length ? (
            <div className="vertical-timeline font-mono scrollable" style={{ maxHeight: "35vh", overflowY: "auto", paddingRight: 6 }}>
              {timeline.map((event) => {
                let dotColor = "var(--unaligned)";
                if (["betray", "data_heist", "bankrupt"].includes(event.type)) dotColor = "var(--bad)";
                else if (["help", "mutual_aid", "found_business"].includes(event.type)) dotColor = "var(--good)";
                else if (["lockdown", "shakedown"].includes(event.type)) dotColor = "var(--warn)";
                
                return (
                  <div key={event.id} className="timeline-node">
                    <div className="timeline-line"></div>
                    <div className="timeline-dot" style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}` }}></div>
                    <div className="timeline-content">
                      <div className="timeline-day font-mono">DAY {event.day} · {event.time}</div>
                      <div className="timeline-text">{event.text}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="muted font-mono" style={{ fontSize: 11 }}>No timeline packets recorded yet.</div>
          )}
        </>
      )}

      {tab === "sublink" && (
        <div className="sublink-panel">
          <div className="section-title">Cognitive Sublink: {agent.name.toUpperCase()}</div>
          <div className="font-mono" style={{ fontSize: 9, padding: "0 16px 8px 16px", color: "var(--accent)" }}>
            * Procedural fallback active (Full LLM chat available when run locally with Ollama)
          </div>
          
          <div className="sublink-messages font-mono scrollable" style={{ height: "40vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, paddingRight: 6, marginBottom: 12 }}>
            <div className="sublink-msg system">
              <span className="time">[SYSTEM]</span>
              <span className="text">Secure quantum sublink established. ICE status: BYPASSED.</span>
            </div>
            
            {sublinkHistory.map((m, idx) => (
              <div key={idx} className={`sublink-msg ${m.sender}`}>
                <span className="time">{m.sender === "user" ? "[OBSERVER]" : `[${agent.name.split(" ")[0].toUpperCase()}]`}</span>
                <span className="text">{m.text}</span>
              </div>
            ))}
            
            {sublinkLoading && (
              <div className="sublink-msg agent typing">
                <span className="time">[{agent.name.split(" ")[0].toUpperCase()}]</span>
                <span className="text blink">... TRANSMITTING BRAIN STATE ...</span>
              </div>
            )}
          </div>
          
          <form
            className="sublink-input-area"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!userMsg.trim() || sublinkLoading) return;
              
              const userMsgText = userMsg.trim();
              setUserMsg("");
              setSublinkLoading(true);
              
              const updatedHistory = [...sublinkHistory, { sender: "user", text: userMsgText }];
              setSublinkHistory(updatedHistory);
              
              try {
                const res = await api.chatWithAgent(agent.id, userMsgText, sublinkHistory);
                setSublinkHistory([...updatedHistory, { sender: "agent", text: res.text }]);
              } catch (err) {
                console.error(err);
                setSublinkHistory([...updatedHistory, { sender: "system", text: "CONNECTION TERMINATED. TELEMETRY EXCEPTION." }]);
              } finally {
                setSublinkLoading(false);
              }
            }}
            style={{ display: "flex", gap: 8 }}
          >
            <input
              type="text"
              className="sublink-input font-mono"
              value={userMsg}
              onChange={(e) => setUserMsg(e.target.value)}
              placeholder="Inject cognitive pulse..."
              disabled={sublinkLoading}
              style={{ flex: 1 }}
            />
            <button type="submit" className="sublink-send-btn font-mono" disabled={sublinkLoading}>
              SEND
            </button>
          </form>
        </div>
      )}

      {tab === "chats" && (
        <>
          <div className="section-title">Recent Conversations</div>
          <div className="chats-container" style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "52vh", overflowY: "auto", paddingRight: 4 }}>
            {chats.map((c, i) => (
              <div key={i} className="chat-block" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px", background: "rgba(255,255,255,0.02)" }}>
                {c.map((line, li) => {
                  const isMe = line.speaker === agent.name;
                  return (
                    <div key={li} style={{ display: "flex", flexDirection: "column", alignItems: isMe ? "flex-end" : "flex-start", margin: "5px 0" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--muted)", margin: "0 4px", fontWeight: 500 }}>{line.speaker}</span>
                      <div style={{
                        background: isMe ? "var(--accent)" : "rgba(255,255,255,0.06)",
                        color: isMe ? "#000" : "var(--fg)",
                        padding: "6px 10px",
                        borderRadius: isMe ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                        maxWidth: "85%",
                        fontSize: "0.85rem",
                        marginTop: 2,
                        lineHeight: 1.35
                      }}>
                        {line.text}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
            {chats.length === 0 && <div className="muted">No conversations logged yet.</div>}
          </div>
        </>
      )}
    </div>
  );
}
