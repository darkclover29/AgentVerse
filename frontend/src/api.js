import * as staticEngine from "./staticReplay.js";

const base = import.meta.env.VITE_API_BASE_URL || "";

let initPromise = null;
let useStaticMode = false;
let currentDay = 0;
let currentTick = 0;

export async function checkModeAndInit() {
  if (initPromise) return initPromise;
  
  initPromise = (async () => {
    // Check if backend is alive
    try {
      const res = await fetch(`${base}/api/health`);
      if (res.ok) {
        useStaticMode = false;
        console.log("[API] Backend is online. Using live API.");
        return;
      }
    } catch (err) {
      // Backend offline
    }
    
    console.log("[API] Backend is offline. Initializing static replay mode...");
    useStaticMode = true;
    try {
      const res = await fetch("./replay_data.json");
      const data = await res.json();
      staticEngine.initialize(data);
    } catch (err) {
      console.error("[API] Failed to load replay_data.json:", err);
    }
  })();
  
  return initPromise;
}

export function isStatic() {
  return useStaticMode;
}

export function setStaticClock(day, tick) {
  currentDay = day;
  currentTick = tick;
}

export function getStaticLogs() {
  if (useStaticMode) {
    return staticEngine.reconstructState(currentDay, currentTick).logs;
  }
  return [];
}

export async function getWorld() {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getGrid();
  }
  return (await fetch(`${base}/api/world`)).json();
}

export async function getAgents() {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.reconstructState(currentDay, currentTick).agents;
  }
  return (await fetch(`${base}/api/agents`)).json();
}

export async function getClock() {
  await checkModeAndInit();
  if (useStaticMode) {
    const state = staticEngine.reconstructState(currentDay, currentTick);
    return {
      day: currentDay,
      tick: currentTick,
      kitty_pool: state.kittyPool
    };
  }
  return (await fetch(`${base}/api/clock`)).json();
}

export async function getNews(day) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getNews(day);
  }
  return (await fetch(`${base}/api/news?day=${day}`)).json();
}

export async function getNewspaper(day) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getNewspaper(day);
  }
  return (await fetch(`${base}/api/newspaper?day=${day}`)).json();
}

export async function getGraph() {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getGraph(currentDay, currentTick);
  }
  return (await fetch(`${base}/api/graph`)).json();
}

export async function getPlan(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getPlan(id, currentDay);
  }
  return (await fetch(`${base}/api/agents/${id}/plan`)).json();
}

export async function getMemories(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    return { agent_id: id, memories: [] };
  }
  return (await fetch(`${base}/api/agents/${id}/memories`)).json();
}

export async function getRelationships(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    const state = staticEngine.reconstructState(currentDay, currentTick);
    const names = Object.fromEntries(state.agents.map(a => [a.id, a.name]));
    const rels = state.relationships
      .filter(r => r.a_id === id)
      .map(r => ({
        id: r.b_id,
        name: names[r.b_id] || `Agent ${r.b_id}`,
        trust: r.trust,
        friendship: r.friendship,
        rivalry: r.rivalry
      }));
    rels.sort((a, b) => Math.max(b.friendship, b.rivalry) - Math.max(a.friendship, a.rivalry));
    return {
      agent_id: id,
      relationships: rels.slice(0, 12)
    };
  }
  return (await fetch(`${base}/api/agents/${id}/relationships`)).json();
}

export async function getStatus() {
  await checkModeAndInit();
  if (useStaticMode) {
    return { ollama: false, chroma: false, model: "heuristic planner (static replay)" };
  }
  return (await fetch(`${base}/api/status`)).json();
}

export async function getBusinesses() {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.reconstructState(currentDay, currentTick).businesses;
  }
  return (await fetch(`${base}/api/businesses`)).json();
}

export async function getHistory(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getHistory(id, currentDay);
  }
  return (await fetch(`${base}/api/agents/${id}/history`)).json();
}

export async function getReplay(day) {
  await checkModeAndInit();
  if (useStaticMode) {
    return {
      day,
      agents: staticEngine.reconstructState(day, 23).agents
    };
  }
  return (await fetch(`${base}/api/replay?day=${day}`)).json();
}

export async function step(ticks = 1) {
  await checkModeAndInit();
  if (useStaticMode) {
    currentTick += ticks;
    while (currentTick >= 24) {
      currentTick -= 24;
      currentDay += 1;
    }
    if (currentDay > 30) {
      currentDay = 30;
      currentTick = 23;
    }
    const state = staticEngine.reconstructState(currentDay, currentTick);
    return { day: currentDay, tick: currentTick, kitty_pool: state.kittyPool };
  }
  return (
    await fetch(`${base}/api/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticks }),
    })
  ).json();
}

export async function reset() {
  await checkModeAndInit();
  if (useStaticMode) {
    currentDay = 0;
    currentTick = 0;
    const state = staticEngine.reconstructState(0, 0);
    return { day: 0, tick: 0, kitty_pool: state.kittyPool };
  }
  return (await fetch(`${base}/api/reset`, { method: "POST" })).json();
}

export async function getAgentChats(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getAgentChats(id, currentDay);
  }
  return (await fetch(`${base}/api/agents/${id}/chats`)).json();
}

export async function getAgentTimeline(id) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.getAgentTimeline(id, currentDay);
  }
  return (await fetch(`${base}/api/agents/${id}/timeline`)).json();
}

export async function chatWithAgent(id, message, history) {
  await checkModeAndInit();
  if (useStaticMode) {
    return staticEngine.chatWithAgent(id, message, currentDay, currentTick);
  }
  return (
    await fetch(`${base}/api/agents/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    })
  ).json();
}

export async function updateTile(x, y, type) {
  await checkModeAndInit();
  if (useStaticMode) {
    return { status: "ok" };
  }
  return (
    await fetch(`${base}/api/world/tile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x, y, type }),
    })
  ).json();
}

export async function reproject() {
  await checkModeAndInit();
  if (useStaticMode) {
    return { status: "ok", replayed_events: 0 };
  }
  return (await fetch(`${base}/api/reproject`, { method: "POST" })).json();
}

export function openSocket(onMessage) {
  if (useStaticMode) {
    return { close: () => {} };
  }
  let wsUrl;
  if (base) {
    try {
      const parsed = new URL(base, location.href);
      const proto = parsed.protocol === "https:" ? "wss" : "ws";
      wsUrl = `${proto}://${parsed.host}/ws`;
    } catch (e) {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      wsUrl = `${proto}://${location.host}/ws`;
    }
  } else {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    wsUrl = `${proto}://${location.host}/ws`;
  }
  const sock = new WebSocket(wsUrl);
  sock.onmessage = (e) => onMessage(JSON.parse(e.data));
  return sock;
}

export async function getEnvironment(day, tick) {
  await checkModeAndInit();
  if (useStaticMode) {
    const isMonsoon = (d) => (d % 5) === 2 || (d % 5) === 3;
    const getAqi = (d, t) => {
      let base = 100 + (d * 8) % 150;
      if (t >= 7 && t <= 18) {
        const peakAdder = t < 13 ? (t - 7) * 25 : (18 - t) * 25;
        base += peakAdder;
      }
      return Math.round(base);
    };
    const getAqiStatus = (aqi) => {
      if (aqi < 100) return "GOOD";
      if (aqi < 200) return "MODERATE";
      if (aqi < 300) return "POOR";
      if (aqi < 400) return "VERY POOR";
      return "SEVERE";
    };
    
    const targetDay = day !== undefined ? day : currentDay;
    const targetTick = tick !== undefined ? tick : currentTick;
    const aqi = getAqi(targetDay, targetTick);
    
    return {
      day: targetDay,
      tick: targetTick,
      is_monsoon: isMonsoon(targetDay),
      flooded_tiles: [],
      aqi_level: aqi,
      aqi_status: getAqiStatus(aqi),
      is_traffic_gridlock: (targetTick >= 7 && targetTick <= 9) || (targetTick >= 16 && targetTick <= 18),
      gridlock_tiles: []
    };
  }
  
  let url = `${base}/api/environment`;
  if (day !== undefined && tick !== undefined) {
    url += `?day=${day}&tick=${tick}`;
  }
  return (await fetch(url)).json();
}

