import { useEffect, useState, useRef } from "react";
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

export default function AgentDossierModal({ agent, onClose }) {
  const [plan, setPlan] = useState(null);
  const [memories, setMemories] = useState([]);
  const [rels, setRels] = useState([]);
  const [history, setHistory] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [sublinkHistory, setSublinkHistory] = useState([]);
  const [userMsg, setUserMsg] = useState("");
  const [sublinkLoading, setSublinkLoading] = useState(false);
  const [businessInfo, setBusinessInfo] = useState([]);
  const msgEndRef = useRef(null);

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
    api.getAgentTimeline(agent.id).then(setTimeline);
    api.getBusinesses().then((bizList) => {
      // Find businesses owned or worked at by this agent
      const related = bizList.filter(b => b.owner_id === agent.id || (b.employees && b.employees.includes(agent.id)));
      setBusinessInfo(related);
    });
  }, [agent]);

  useEffect(() => {
    // Scroll to bottom of message list on new message
    msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sublinkHistory, sublinkLoading]);

  if (!agent) return null;

  // Compute dynamic evolution of character based on stats & timeline history
  function getEvolvingStatus() {
    let physical = "Stable. Standard daily hustle levels.";
    if (agent.energy >= 80) physical = "Energetic. Synaptic speed optimal, fueled by double Adrak Chai.";
    else if (agent.energy < 30) physical = "⚠️ EXHAUSTED. Synaptic latency high. Got stuck in a 3-hour Silk Board traffic jam.";

    let psychology = "Normal. Average metropolis sanity index.";
    if (agent.happiness >= 75) psychology = "Extremely chill. Sipping hot tea during monsoons.";
    else if (agent.happiness < 30) psychology = "⚠️ HYPER-STRESSED. On the verge of road rage. Desi-stress levels critical.";

    let archetype = `${agent.personality.toUpperCase()} · Standard Desi citizen.`;
    const hasBetrayal = timeline.some(e => e.type === "betray");
    const hasHeist = timeline.some(e => e.type === "data_heist");
    const hasMutualAid = timeline.some(e => e.type === "mutual_aid");
    const hasShakedown = timeline.some(e => e.type === "shakedown");
    const hasBankruptcy = timeline.some(e => e.type === "bankrupt");

    if (hasBetrayal) archetype = "SKEPTICAL CITIZEN · Wary of local scams and false promises after documented betrayal.";
    else if (hasHeist) archetype = "JUGAAD MOONLIGHTER · Actively moonlighting and siphoning corporate tech contracts.";
    else if (hasMutualAid) archetype = "MOHALLA COMMITTEE LEADER · Organizing local community funds, help networks, and kitty parties.";
    else if (hasShakedown) archetype = "AUTO STAND UNION BOSS · Collecting parking dues, tanker cartels, and protection money.";
    else if (hasBankruptcy) archetype = "RESILIENT DUKANDAR · Rebuilding local tea/samosa shop after a municipal corporation drive.";

    return { physical, psychology, archetype };
  }

  const { physical, psychology, archetype } = getEvolvingStatus();

  return (
    <div className="dossier-overlay glass">
      <div className="dossier-modal">
        {/* Header HUD */}
        <div className="dossier-header-bar">
          <div className="dossier-title font-mono">
            <span className="blink">■</span> NEURAL_DOSSIER_HUD // ID_{agent.id.toString().padStart(4, "0")}
          </div>
          <button className="dossier-close-btn" onClick={onClose} aria-label="Close">
            <Icon.Close /> CLOSE CONSOLE
          </button>
        </div>

        <div className="dossier-grid">
          {/* LEFT COLUMN: Identity & Bio-Telemetry */}
          <div className="dossier-col-left scrollable">
            <div className="dossier-card-header font-mono">1. BIOMETRIC_IDENTIFICATION</div>
            
            {/* Visual HUD Avatar */}
            <div className="dossier-avatar-hud">
              <svg viewBox="0 0 120 120" className="dossier-svg">
                <circle cx="60" cy="60" r="55" stroke="rgba(52, 208, 191, 0.08)" strokeWidth="1" fill="none" />
                <circle cx="60" cy="60" r="48" stroke="rgba(52, 208, 191, 0.15)" strokeWidth="1.5" strokeDasharray="5 5" fill="none" className="rot-cw" />
                <circle cx="60" cy="60" r="38" stroke="var(--accent)" strokeWidth="1" strokeDasharray="40 180" fill="none" className="rot-ccw" />
                <path d="M60 10 L60 110 M10 60 L110 60" stroke="rgba(52, 208, 191, 0.1)" strokeWidth="0.5" />
                <path d="M48,50 Q60,35 72,50 Q75,60 69,75 Q60,82 51,75 Q45,60 48,50 Z" stroke="var(--accent)" strokeWidth="1" fill="none" style={{ filter: "drop-shadow(0 0 3px var(--accent))" }} />
                <circle cx="53" cy="50" r="2.5" fill="var(--accent)" />
                <circle cx="67" cy="50" r="2.5" fill="var(--accent)" />
                <path d="M56,60 Q60,63 64,60" stroke="var(--accent)" strokeWidth="1" fill="none" />
                <path d="M53,68 Q60,72 67,68" stroke="rgba(255, 255, 255, 0.4)" strokeWidth="1" fill="none" />
              </svg>
              <div className="dossier-telemetry font-mono">
                <div className="name-line">{agent.name.toUpperCase()}</div>
                <div>AGE: <span className="val">{agent.age}</span></div>
                <div>GENDER: <span className="val">{agent.gender}</span></div>
                <div>FACTION: <span className="val" style={{ color: FACTION_COLOR[agent.faction], textShadow: `0 0 4px ${FACTION_COLOR[agent.faction]}` }}>{(FACTION_LABEL[agent.faction] || agent.faction).toUpperCase()}</span></div>
                <div>CLASS: <span className="val">{(OCCUPATION_LABEL[agent.occupation] || agent.occupation).toUpperCase()}</span></div>
                <div>COGNITION: <span className="val">{agent.tier === 2 ? "SECURE_LLM (★ T2)" : "HEURISTIC_RULES"}</span></div>
              </div>
            </div>

            <div className="dossier-card-header font-mono" style={{ marginTop: 20 }}>2. CHRONOLOGICAL_BACKGROUND</div>
            <div className="dossier-bio-text">{agent.background}</div>

            <div className="dossier-card-header font-mono" style={{ marginTop: 20 }}>3. NEURAL_EVOLUTION_PROFILE</div>
            <div className="dossier-neuro-status font-mono">
              <div className="status-row">
                <span className="lbl">ARCHETYPE:</span>
                <span className="val text-accent">{archetype}</span>
              </div>
              <div className="status-row">
                <span className="lbl">PSYCHOLOGY:</span>
                <span className="val">{psychology}</span>
              </div>
              <div className="status-row">
                <span className="lbl">NEURO-STAMINA:</span>
                <span className="val">{physical}</span>
              </div>
            </div>

            <div className="dossier-card-header font-mono" style={{ marginTop: 20 }}>4. FINANCIAL_LEDGER & VENTURES</div>
            <div className="dossier-finance-hud font-mono">
              <div className="finance-row">
                <span className="lbl">LIQUID_WEALTH:</span>
                <span className="val text-good">₹{Math.round(agent.wealth)}</span>
              </div>
              <div className="finance-row">
                <span className="lbl">CREDIT_SCORE:</span>
                <span className="val">{agent.wealth > 150 ? "AAA (Optimal)" : agent.wealth > 60 ? "BBB (Secure)" : "C- (Deficient)"}</span>
              </div>
              
              {businessInfo.length > 0 ? businessInfo.map((b) => (
                <div key={b.id} className="dossier-biz-box">
                  <div style={{ color: "var(--warn)", fontWeight: "bold" }}>VENTURE: {b.name.toUpperCase()}</div>
                  <div>ROLE: {b.owner_id === agent.id ? "OWNER / CEO" : "CONTRACT EMPLOYEE"}</div>
                  <div>CAPITALIZATION: ₹{Math.round(b.capital)}</div>
                  <div>STATUS: <span style={{ color: b.status === "open" ? "var(--good)" : "var(--bad)" }}>{b.status.toUpperCase()}</span></div>
                </div>
              )) : (
                <div className="muted font-mono" style={{ fontSize: 11, marginTop: 6 }}>No business holdings or employment registered.</div>
              )}
            </div>
          </div>

          {/* MIDDLE COLUMN: Direct Agent Communication Console */}
          <div className="dossier-col-mid">
            <div className="dossier-card-header font-mono">5. COGNITIVE_SUBLINK_TERMINAL</div>
            
            <div className="dossier-chat-panel">
              <div style={{ fontSize: 9, color: "var(--warn)", padding: "5px 10px", borderBottom: "1px solid var(--border)", background: "rgba(255, 193, 7, 0.05)" }} className="font-mono">
                NOTICE: PROCEDURAL FALLBACK ACTIVE. FULL LLM COGNITION AVAILABLE WHEN RUN LOCALLY WITH OLLAMA.
              </div>
              <div className="dossier-chat-messages font-mono scrollable">
                <div className="sublink-msg system">
                  <span className="time">[SYSTEM_LOG]</span>
                  <span className="text">Secure quantum sublink established. Bypass protocols active. Observational monitoring enabled.</span>
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
                <div ref={msgEndRef} />
              </div>

              <form
                className="dossier-chat-input-area"
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
                    setSublinkHistory([...updatedHistory, { sender: "system", text: "CONNECTION DISRUPTED. TELEMETRY BUFFER OUT OF BOUNDS." }]);
                  } finally {
                    setSublinkLoading(false);
                  }
                }}
              >
                <span className="terminal-prompt font-mono">&gt;&gt;</span>
                <input
                  type="text"
                  className="dossier-chat-input font-mono"
                  value={userMsg}
                  onChange={(e) => setUserMsg(e.target.value)}
                  placeholder="Inject cognitive neural pulse..."
                  disabled={sublinkLoading}
                />
                <button type="submit" className="dossier-chat-send-btn font-mono" disabled={sublinkLoading}>
                  TRANSMIT
                </button>
              </form>
            </div>
          </div>

          {/* RIGHT COLUMN: Life Events Timeline */}
          <div className="dossier-col-right scrollable">
            <div className="dossier-card-header font-mono">6. HISTORICAL_EVENT_PACKETS</div>
            
            {timeline.length ? (
              <div className="vertical-timeline font-mono" style={{ margin: "10px 0" }}>
                {timeline.map((event) => {
                  let dotColor = "var(--unaligned)";
                  if (["betray", "data_heist", "bankrupt"].includes(event.type)) dotColor = "var(--bad)";
                  else if (["help", "mutual_aid", "found_business"].includes(event.type)) dotColor = "var(--good)";
                  else if (["lockdown", "shakedown"].includes(event.type)) dotColor = "var(--warn)";
                  
                  return (
                    <div key={event.id} className="timeline-node" style={{ paddingBottom: 15 }}>
                      <div className="timeline-line"></div>
                      <div className="timeline-dot" style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}`, width: 7, height: 7, left: -18, top: 6 }}></div>
                      <div className="timeline-content" style={{ padding: "8px 10px" }}>
                        <div className="timeline-day font-mono" style={{ fontSize: 9 }}>DAY {event.day} · {event.time}</div>
                        <div className="timeline-text" style={{ fontSize: 10.5 }}>{event.text}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="muted font-mono" style={{ fontSize: 11, padding: 10 }}>No timeline packets recorded on this grid node.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
