// Client-side event-sourced fold engine for zero-backend static replay mode

let replayData = null;

// Cache for reconstructed state at specific (day, tick) to avoid re-folding on every request
const stateCache = {};

export function initialize(data) {
  replayData = data;
  // Clear cache on re-initialization
  for (const k in stateCache) delete stateCache[k];
  console.log(`[StaticReplay] Initialized with ${data.events.length} events across 30 days.`);
}

export function isInitialized() {
  return replayData !== null;
}

export function getGrid() {
  if (!replayData) return { tiles: [], grid_size: 20 };
  return {
    grid_size: replayData.grid_size || 20,
    tiles: replayData.grid_tiles || []
  };
}

export function reconstructState(targetDay, targetTick) {
  if (!replayData) return { agents: [], relationships: [], businesses: [], kittyPool: 100, logs: [] };

  const cacheKey = `${targetDay}-${targetTick}`;
  if (stateCache[cacheKey]) {
    return stateCache[cacheKey];
  }

  // Deep clone initial agents
  const agents = {};
  replayData.initial_agents.forEach(a => {
    agents[a.id] = { ...a };
  });

  // Setup relationships map (Directed relationship key: "a_id-b_id")
  const rels = {};
  replayData.initial_relationships.forEach(r => {
    rels[`${r.a_id}-${r.b_id}`] = { ...r };
  });

  const getRel = (aId, bId) => {
    const key = `${aId}-${bId}`;
    if (!rels[key]) {
      rels[key] = { a_id: aId, b_id: bId, trust: 0.0, friendship: 0.0, rivalry: 0.0 };
    }
    return rels[key];
  };

  const clamp = (v, lo = -100, hi = 100) => Math.max(lo, Math.min(hi, v));

  // Reconstruct businesses list
  const businesses = {};

  // Filter events up to (targetDay, targetTick)
  const filteredEvents = replayData.events.filter(e => {
    if (e.day < targetDay) return true;
    if (e.day === targetDay && e.tick <= targetTick) return true;
    return false;
  });

  let kittyPool = 100.0;
  const logs = [];

  // Fold events!
  filteredEvents.forEach(e => {
    const agent = agents[e.agent_id];
    const p = e.payload || {};

    if (e.type === "move" && agent) {
      agent.x = p.x !== undefined ? p.x : agent.x;
      agent.y = p.y !== undefined ? p.y : agent.y;
      agent.energy = clamp(agent.energy - 1.0, 0, 100);
    } 
    else if (e.type === "earn" && agent) {
      agent.wealth += p.amount || 0;
      agent.energy = clamp(agent.energy - 5.0, 0, 100);
    } 
    else if (e.type === "work" && agent) {
      agent.wealth += p.amount || 0;
      agent.energy = clamp(agent.energy - 8.0, 0, 100);
      agent.happiness = clamp(agent.happiness + (p.happiness || 0), 0, 100);
    } 
    else if (e.type === "job_change" && agent) {
      agent.occupation = p.occupation || agent.occupation;
    } 
    else if (e.type === "sleep" && agent) {
      agent.energy = 100.0;
    } 
    else if (e.type === "socialize" && agent && e.target_id) {
      agent.happiness = clamp(agent.happiness + 3.0, 0, 100);
      [
        [e.agent_id, e.target_id],
        [e.target_id, e.agent_id]
      ].forEach(([x, y]) => {
        const r = getRel(x, y);
        r.friendship = clamp(r.friendship + 5.0);
        r.trust = clamp(r.trust + 2.0);
      });
    } 
    else if (e.type === "help" && agent && e.target_id) {
      const r = getRel(e.target_id, e.agent_id);
      r.trust = clamp(r.trust + 10.0);
      r.friendship = clamp(r.friendship + 5.0);
    } 
    else if (e.type === "betray" && agent && e.target_id) {
      const r = getRel(e.target_id, e.agent_id);
      r.trust = clamp(r.trust - 15.0);
      r.rivalry = clamp(r.rivalry + 12.0);
    } 
    else if (e.type === "found_business") {
      if (agent) {
        agent.wealth -= 120.0;
      }
      businesses[p.name] = {
        id: Object.keys(businesses).length + 1,
        name: p.name,
        btype: p.btype,
        owner_id: e.agent_id,
        x: agent ? agent.x : (p.x || 0),
        y: agent ? agent.y : (p.y || 0),
        capital: 120.0,
        employees: [],
        day_founded: e.day,
        status: "open"
      };
    } 
    else if (e.type === "hire") {
      const biz = businesses[p.business];
      const candidate = agents[e.target_id];
      if (biz && candidate && biz.status === "open") {
        if (!biz.employees.includes(candidate.id)) {
          biz.employees = [...biz.employees, candidate.id];
        }
        candidate.occupation = `${biz.btype} worker`;
      }
    } 
    else if (e.type === "revenue") {
      const biz = businesses[p.business];
      if (biz && biz.status === "open") {
        const net = p.net || 0.0;
        const adjust = p.adjust !== undefined ? p.adjust : net;
        biz.capital += adjust;
        if (net > 0) {
          const owner = agents[e.agent_id];
          if (owner) {
            owner.wealth += net * 0.5;
            biz.capital -= net * 0.5;
          }
        }
        (biz.employees || []).forEach(empId => {
          const emp = agents[empId];
          if (emp) {
            emp.wealth += 12.0; // WAGE
          }
        });
      }
    } 
    else if (e.type === "bankrupt") {
      const biz = businesses[p.business];
      if (biz) {
        biz.status = "bankrupt";
        (biz.employees || []).forEach(empId => {
          const emp = agents[empId];
          if (emp) {
            emp.occupation = "unemployed";
          }
        });
        biz.employees = [];
      }
    } 
    else if (e.type === "consume" && agent) {
      const cost = p.amount || 15.0;
      agent.wealth -= cost;
      if (p.business_id) {
        const biz = Object.values(businesses).find(b => b.id === p.business_id);
        if (biz) {
          biz.capital += cost;
        }
      }
      if (p.need === "energy") {
        agent.energy = clamp(agent.energy + 40.0, 0, 100);
      } else {
        agent.happiness = clamp(agent.happiness + 25.0, 0, 100);
      }
    } 
    else if (e.type === "data_heist") {
      const biz = Object.values(businesses).find(b => b.id === p.business_id);
      if (biz) biz.capital -= p.amount || 40.0;
      if (agent) agent.wealth += p.amount || 40.0;
    } 
    else if (e.type === "shakedown") {
      const biz = Object.values(businesses).find(b => b.id === p.business_id);
      if (biz) biz.capital -= p.amount || 25.0;
      if (agent) agent.wealth += p.amount || 25.0;
    } 
    else if (e.type === "lockdown") {
      const biz = Object.values(businesses).find(b => b.id === p.business_id);
      if (biz) biz.capital -= p.amount || 30.0;
    } 
    else if (e.type === "mutual_aid") {
      const amount = p.amount || 50.0;
      let payout = amount;
      if (kittyPool < payout) {
        payout = Math.max(0.0, kittyPool);
      }
      kittyPool = Math.max(0.0, kittyPool - payout);
      if (p.business_id) {
        const biz = Object.values(businesses).find(b => b.id === p.business_id);
        if (biz) biz.capital += payout;
      } else {
        const receiver = agents[e.agent_id];
        if (receiver) receiver.wealth += payout;
      }
    } 
    else if (e.type === "kitty_party") {
      const participants = p.participants || [];
      const contrib = 15.0;
      let totalContrib = 0.0;
      participants.forEach(pid => {
        const pa = agents[pid];
        if (pa) {
          pa.wealth = Math.max(0.0, pa.wealth - contrib);
          pa.happiness = clamp(pa.happiness + 15.0, 0, 100);
          totalContrib += contrib;
        }
      });
      kittyPool += totalContrib;
      for (let i = 0; i < participants.length; i++) {
        for (let j = i + 1; j < participants.length; j++) {
          [
            [participants[i], participants[j]],
            [participants[j], participants[i]]
          ].forEach(([x, y]) => {
            const r = getRel(x, y);
            r.friendship = clamp(r.friendship + 4.0);
            r.trust = clamp(r.trust + 2.0);
          });
        }
      }
    }

    // Format console logs
    if (e.importance >= 0.5 || ["found_business", "hire", "revenue", "bankrupt", "consume", "betray", "help", "data_heist", "shakedown", "lockdown", "mutual_aid", "chat"].includes(e.type)) {
      const actorName = agent ? agent.name : `Agent ${e.agent_id}`;
      const targetName = e.target_id && agents[e.target_id] ? agents[e.target_id].name : "";
      let text = "";
      if (e.type === "found_business") text = `${actorName} opened ${p.name || "business"}.`;
      else if (e.type === "hire") text = `${actorName} hired ${targetName} at ${p.business || "venture"}.`;
      else if (e.type === "revenue") text = `${p.business} generated ₹${p.net} net revenue.`;
      else if (e.type === "bankrupt") text = `⚠️ ${p.business} went bankrupt!`;
      else if (e.type === "consume") text = `${actorName} spent ₹${p.amount} on ${p.need === "energy" ? "Adrak Chai" : "Chai & Snacks"}.`;
      else if (e.type === "betray") text = `⚔️ ${actorName} betrayed ${targetName}!`;
      else if (e.type === "help") text = `🤝 ${actorName} helped ${targetName}.`;
      else if (e.type === "data_heist") text = `💾 Moonlighter ${actorName} siphoned ₹${p.amount} from ${p.business_name}.`;
      else if (e.type === "shakedown") text = `💸 Auto Union ${actorName} extorted ₹${p.amount} from ${p.business_name}.`;
      else if (e.type === "lockdown") text = `🚨 Authority ${actorName} fined ${p.business_name} ₹${p.amount}.`;
      else if (e.type === "mutual_aid") text = `✊ Mohalla Committee pooled ₹${p.amount} for ${p.business_name}.`;
      else if (e.type === "chat") {
        const firstLine = p.dialogue && p.dialogue[0] ? p.dialogue[0].text : "";
        text = `💬 ${actorName} spoke with ${targetName}: "${firstLine.substring(0, 40)}..."`;
      } else {
        text = `${actorName} performed: ${e.type}.`;
      }

      const category = ["betray", "data_heist", "shakedown", "lockdown"].includes(e.type)
        ? "security"
        : ["found_business", "revenue", "bankrupt", "consume", "mutual_aid"].includes(e.type)
        ? "financial"
        : "social";

      logs.push({
        id: e.id,
        day: e.day,
        tick: e.tick,
        time: `${String(e.tick).padStart(2, "0")}:00`,
        text,
        faction: agent ? agent.faction : "unaligned",
        category
      });
    }
  });

  const agentsList = Object.values(agents);
  const businessesList = Object.values(businesses);

  const result = {
    agents: agentsList,
    relationships: Object.values(rels),
    businesses: businessesList,
    kittyPool,
    logs: logs.slice(-100)
  };

  // Cache results
  stateCache[cacheKey] = result;
  return result;
}

export function getNews(day) {
  if (!replayData) return { day, headlines: [] };
  
  // Format headlines dynamically based on events of that day
  const dayEvents = replayData.events.filter(e => e.day === day && e.importance >= 0.5);
  const names = Object.fromEntries(replayData.initial_agents.map(a => [a.id, a.name]));

  const headlines = dayEvents.map(e => {
    const actor = names[e.agent_id] || `Agent ${e.agent_id}`;
    const target = names[e.target_id] || "";
    const p = e.payload || {};

    if (e.type === "found_business") {
      return `${actor} opened ${p.name || "a new business"}.`;
    } else if (e.type === "bankrupt") {
      return `${p.business || "A business"} went under — ${actor} ruined.`;
    } else if (e.type === "hire") {
      return `${actor} hired ${target} at ${p.business || "their venture"}.`;
    } else if (e.type === "revenue" && (p.net || 0) < 0) {
      return `${p.business || "A business"} is bleeding money.`;
    } else if (e.type === "plan") {
      return `${actor} set out to ${p.goal || "a new scheme"}`;
    } else if (e.type === "betray") {
      return `${actor} turned on ${target} — trust shattered.`;
    } else if (e.type === "help") {
      return `${actor} backed {target} in a tight spot.`;
    } else if (e.type === "job_change") {
      return `${actor} took up work as a ${p.occupation || "a new role"}.`;
    } else {
      return `${actor}: ${e.type}`;
    }
  });

  // Limit to 8 headlines
  return {
    day,
    headlines: headlines.slice(0, 8)
  };
}

export function getNewspaper(day) {
  if (!replayData) return null;
  return replayData.newspapers[day] || replayData.newspapers["0"] || null;
}

export function getGraph(day, tick) {
  const state = reconstructState(day, tick);
  const minStrength = 10.0;
  
  const nodes = state.agents.map(a => ({
    id: a.id,
    name: a.name,
    faction: a.faction,
    occupation: a.occupation
  }));

  const edges = [];
  const seen = new Set();

  state.relationships.forEach(r => {
    const key = [r.a_id, r.b_id].sort().join("-");
    if (seen.has(key)) return;
    seen.add(key);

    if (r.rivalry >= minStrength) {
      edges.append = edges.push({ source: r.a_id, target: r.b_id, kind: "rivalry", weight: r.rivalry });
    } else if (r.friendship >= minStrength) {
      edges.push({ source: r.a_id, target: r.b_id, kind: "friendship", weight: r.friendship });
    }
  });

  return { nodes, edges };
}

export function getPlan(agentId, currentDay) {
  if (!replayData) return { agent_id: agentId, goal: null, steps: [], step_index: 0 };

  const agentPlans = replayData.plans.filter(p => p.agent_id === agentId && p.day_created <= currentDay);
  if (agentPlans.length === 0) {
    return { agent_id: agentId, goal: null, steps: [], step_index: 0 };
  }

  // Find active/latest plan
  agentPlans.sort((a, b) => b.day_created - a.day_created);
  const plan = agentPlans[0];
  const steps = plan.steps || [];
  
  // Estimate step index based on days elapsed since day_created (approx 1 step per day)
  const stepIndex = Math.min(steps.length, Math.max(0, currentDay - plan.day_created));

  return {
    agent_id: agentId,
    goal: plan.goal,
    steps: steps,
    step_index: stepIndex,
    source: plan.source
  };
}

export function getHistory(agentId, currentDay) {
  // Reconstruct agent history day-by-day up to currentDay
  const series = [];
  for (let d = 0; d <= currentDay; d++) {
    const state = reconstructState(d, 23);
    const agent = state.agents.find(a => a.id === agentId);
    if (agent) {
      series.push({
        day: d,
        wealth: Math.round(agent.wealth * 10) / 10,
        happiness: Math.round(agent.happiness * 10) / 10
      });
    }
  }
  return { agent_id: agentId, series };
}

export function getAgentChats(agentId, currentDay) {
  if (!replayData) return { agent_id: agentId, chats: [] };

  const chatEvents = replayData.events.filter(e => 
    e.type === "chat" && 
    e.day <= currentDay && 
    (e.agent_id === agentId || e.target_id === agentId)
  );

  chatEvents.sort((a, b) => b.id - a.id); // latest first
  const chats = chatEvents.slice(0, 20).map(e => e.payload.dialogue || []);

  return { agent_id: agentId, chats };
}

export function getAgentTimeline(agentId, currentDay) {
  if (!replayData) return [];

  const events = replayData.events.filter(e => 
    e.day <= currentDay && 
    e.type !== "move" && 
    (e.agent_id === agentId || e.target_id === agentId)
  );

  events.sort((a, b) => b.day - a.day || b.tick - a.tick || b.id - a.id); // latest first
  const names = Object.fromEntries(replayData.initial_agents.map(a => [a.id, a.name]));

  const timeline = [];
  events.slice(0, 50).forEach(e => {
    const actor = names[e.agent_id] || `Agent ${e.agent_id}`;
    const target = names[e.target_id] || "";
    const p = e.payload || {};
    const isActor = e.agent_id === agentId;
    let text = "";

    if (e.type === "found_business") {
      text = isActor ? `Founded venture '${p.name}'` : `Venture '${p.name}' founded by ${actor}`;
    } else if (e.type === "hire") {
      text = isActor ? `Hired ${target} at '${p.business}'` : `Hired by {actor} at '${p.business}'`;
    } else if (e.type === "bankrupt") {
      text = isActor ? `Went bankrupt! Venture '${p.business}' liquidated.` : `Venture '${p.business}' owned by ${actor} liquidated.`;
    } else if (e.type === "consume") {
      text = `Spent ₹${p.amount} at '${p.business}' for ${p.need} recovery`;
    } else if (e.type === "betray") {
      text = isActor ? `⚠️ Betrayed ${target}!` : `⚡ Betrayed by ${actor}!`;
    } else if (e.type === "help") {
      text = isActor ? `🤝 Helped ${target}` : `🤝 Supported by ${actor}`;
    } else if (e.type === "data_heist") {
      text = isActor ? `💾 Siphoned ₹${p.amount} from ${p.business_name}` : `🚨 Security breached! ${actor} siphoned ₹${p.amount} from your firm '${p.business_name}'`;
    } else if (e.type === "shakedown") {
      text = isActor ? `💸 Extorted ₹${p.amount} from ${p.business_name}` : `💸 Protection payment: Paid ₹${p.amount} to ${actor} for '${p.business_name}'`;
    } else if (e.type === "lockdown") {
      text = isActor ? `🚨 Fined ${p.business_name} ₹${p.amount} during encroachment drive` : `🚨 Fined ₹${p.amount} by Authority ${actor} during encroachment drive of '${p.business_name}'`;
    } else if (e.type === "mutual_aid") {
      text = isActor ? `✊ Contributed ₹${p.amount} to Mohalla fund for ${p.business_name}` : `✊ Received ₹${p.amount} in Mohalla committee aid for '${p.business_name}'`;
    } else if (e.type === "job_change") {
      text = `Changed occupation to ${p.occupation}`;
    } else if (e.type === "chat") {
      const lines = p.dialogue || [];
      const first = lines[0] ? lines[0].text : "...";
      text = isActor ? `💬 Spoke with ${target}: "${first.substring(0, 40)}..."` : `💬 Spoke with ${actor}: "${first.substring(0, 40)}..."`;
    } else if (e.type === "work") {
      text = `Worked shift, earned ₹${p.amount}`;
    } else if (e.type === "earn") {
      text = `Earned side return ₹${p.amount}`;
    } else {
      return; // skip other unformatted types
    }

    timeline.push({
      id: e.id,
      day: e.day,
      tick: e.tick,
      time: `${String(e.tick).padStart(2, "0")}:00`,
      type: e.type,
      text,
      importance: e.importance
    });
  });

  return timeline;
}

export function chatWithAgent(agentId, message, currentDay, currentTick) {
  if (!replayData) return { text: "Neural sublink link lost." };
  
  const state = reconstructState(currentDay, currentTick);
  const agent = state.agents.find(a => a.id === agentId);
  if (!agent) return { text: "Agent not found in registry." };

  const replyText = userChatProceduralFallback(agent, message);
  return { text: replyText };
}

function userChatProceduralFallback(agentCtx, message) {
  const msgLower = message.toLowerCase();
  const faction = agentCtx.faction;
  const name = agentCtx.name;
  const age = agentCtx.age || 25;
  const gender = agentCtx.gender || "Non-binary";
  const occupation = agentCtx.occupation;
  const wealth = Math.round(agentCtx.wealth || 0);

  // Rude / Inappropriate keywords check
  const rudeKeywords = ["nsfw", "18+", "vulgar", "sex", "abuse", "fuck", "bitch", "crap", "dick", "ass", "bastard", "idiot", "inappropriate"];
  if (rudeKeywords.some(k => msgLower.includes(k))) {
    if (faction === "corp") return "This sublink is monitored under municipal telecommunication protocols. Keep your queries professional or I will flag this IP as a security threat.";
    if (faction === "hacker") return "Bro, keep those input sanitizations clean. My local firewall rejects weird requests. Ask about my side-hustle or tech stack instead.";
    if (faction === "syndicate") return "Bhai, dimag mat kharab kar. Rickshaw union rules: no trash talk on our frequency. Keep it civil or get lost.";
    return "Namaste boss, please don't talk like that near my shop. Keep the conversation civil or I'm cutting this neural sublink.";
  }

  // Job / Work
  if (["work", "job", "occupation", "do you do", "earn money"].some(k => msgLower.includes(k))) {
    const jobsMap = {
      executive: "I manage municipal budgets and political permissions. It's a lot of paperwork and meeting local corporators.",
      analyst: "I scan market trends and business cashflows to find where the wealth is moving. Mostly staring at spreadsheets.",
      engineer: "I maintain the tech park servers and write software. Yes, standard IT shift, but I also moon-light.",
      clerk: "I stamp files and manage government files in the municipal office. Come back after lunch, Bhai.",
      netrunner: "I write custom scripts to bypass local server firewalls. Currently optimizing some web scrapers.",
      fixer: "I connect moonlighters with brokers who need data siphoned. I know who sells what in Sector 4.",
      "data-broker": "I package corporate ledger leaks and sell them to the highest bidder at Chor Bazaar.",
      courier: "I deliver physical flash drives and high-priority packages across Indiranagar, dodging traffic.",
      enforcer: "I secure rickshaw stands and collect union dues. If someone doesn't pay, I have to intervene.",
      smuggler: "I drive water tankers and manage illegal supply lines when the municipal pipes run dry.",
      dealer: "I run a side shop selling import electronics and grey-market software under the bridge.",
      lieutenant: "I manage the local stand operators and negotiate turf lines with corporate netas.",
      drifter: "I do odd jobs, sometimes cleaning rickshaws or sweeping tea tapris. Just trying to survive.",
      mechanic: "I repair auto-rickshaw engines and recalibrate faulty meters at Chor Bazaar Gali 3.",
      medic: "I run an informal colony clinic, patching up rickshaw drivers after stand clashes.",
      vendor: "I sell hot dosa and cutting chai near the metro station. Smells good, try some!",
      unemployed: "Currently looking for work. If you have any leads in the market, let know, boss."
    };
    return jobsMap[occupation] || `I make ends meet as a ${occupation}. It pays the bills.`;
  }

  // Faction / Group
  if (["faction", "corp", "hacker", "syndicate"].some(k => msgLower.includes(k))) {
    if (faction === "corp") return "The Municipal Corporation runs this city. Without political permissions, no builder can lay a brick.";
    if (faction === "hacker") return "Freelancers and IT workers run this city's economy! Netas and cartels are just leeching off us.";
    if (faction === "syndicate") return "Auto unions and water tankers keep this city moving. If we strike for one day, the IT tech park will freeze.";
    return "Factions? Politicians want votes, cartels want union dues, techies want apps. I just want my cutting chai in peace.";
  }

  // Wealth / Money
  if (["wealth", "money", "credit", "rich", "rupee", "cash", "earn", "salary", "income", "pay"].some(k => msgLower.includes(k))) {
    if (faction === "corp") return `Government budgets are approved, and my personal ledger sits at ₹${wealth} in savings.`;
    if (faction === "hacker") return `Salary got credited, but after paying PG rent and ordering food, I only have ₹${wealth} left.`;
    if (faction === "syndicate") return `Union fees collection is going strong. My cut is ₹${wealth} in cash right now.`;
    return `Extremely tight budget. After paying the milk vendor, I got ₹${wealth} in my pocket.`;
  }

  // Traffic / City / Silk Board
  if (["traffic", "silk board", "jam", "road", "metro", "city", "bangalore", "location", "where"].some(k => msgLower.includes(k))) {
    if (faction === "corp") return "Municipal road widening proposals are pending review. The current gridlock is due to illegal parking.";
    if (faction === "hacker") return "I spend 2 hours daily at Silk Board. Absolute disaster. I just sit in the cab writing scripts.";
    if (faction === "syndicate") return "Rickshaw fares are double during peak hours at Silk Board. Traffic is literally our business model.";
    return "Vehicles aren't moving at all outside. Better to stay at my tea stall and drink a hot tea.";
  }

  // Plans / Goals
  if (["plan", "goal", "step"].some(k => msgLower.includes(k))) {
    if (faction === "corp") return "My current goal is: execute municipal guidelines and fine illegal auto stands during our next encroachment drive.";
    if (faction === "hacker") return "Plan? Finish my office tickets early so I can build my moonlighting startup project in the PG room.";
    if (faction === "syndicate") return "We control this Metro station. My plan is collecting daily parking dues and keeping other cartels away.";
    return "I am just trying to survive the Silk Board traffic, get some samosas, and get home safely.";
  }

  // Basic greetings
  if (["hi", "hello", "hey", "greet", "namaste", "ram ram"].some(k => msgLower.includes(k))) {
    const greetings = {
      corp: [
        `Namaste. Observer signal verified. I am Corporator ${name}.`,
        "Yes? Municipal office is open. Make it quick.",
        "Observer monitoring active. What do you need?"
      ],
      hacker: [
        "Hey. Decrypted your ping. What's up?",
        "Nice sublink. Almost triggered my security alarms. What's the query?",
        "Observer? Interesting. Got some tech tickets for me?"
      ],
      syndicate: [
        "Ram Ram. Speak up, I have rounds to run.",
        `Rickshaw stand frequency is clear. What do you want, Bhai?`,
        "Observer? Local cartel lines are secure. Make it quick."
      ],
      unaligned: [
        "Namaste, boss. Hot cutting chai is ready. What's the news?",
        "Hello! Need some help navigating the market?",
        "Oh, a neural pulse! Thought my link was glitching. What's up?"
      ]
    };
    const pool = greetings[faction] || ["Hello there."];
    return pool[Math.floor(Math.random() * pool.length)];
  }

  // Fallback messages explaining local LLM
  const fallbacks = {
    corp: [
      "Observer, I am operating on a low-bandwidth procedural backup. To enable my full cognitive planning and chat abilities, run the simulation locally with Ollama active.",
      "This sublink query doesn't match my current ledger instructions. Note that full LLM-driven chat is only active when you run this project locally with Ollama.",
      "Local municipal directories are locked in procedural mode. Run this server locally with Ollama to enable unrestricted AI chat."
    ],
    hacker: [
      "My neural link is in safe-mode backup! I can only give you canned responses here. Run the AgentVerse server locally with Ollama to unlock my full brain power!",
      "Ping received, but I'm running on a low-level fallback script. Download the repository and host it locally with Ollama to chat with my real AI model.",
      "Warning: Local server connection is simulated. Run the project locally with Ollama to bypass this procedural chatbot backup."
    ],
    syndicate: [
      "Signal is weak, Bhai. I'm on a basic procedural frequency. If you want a real, smart conversation, download the repo and run me locally with Ollama.",
      "Rickshaw union bandwidth limits are active on this hosted site. Run the backend locally with Ollama to unlock my full LLM brain.",
      "I can't understand this custom neural pulse on a fallback link. Host the app locally on your machine with Ollama to talk to my full AI model."
    ],
    unaligned: [
      "Sorry boss, my mind is feeling a bit mechanical right now — I'm running on a procedural fallback. To chat with my full LLM brain, run this project locally with Ollama!",
      "Namaste. This hosted demo uses basic canned responses. If you want to experience my full AI-powered dialogue, start the project locally with Ollama active.",
      "My neural link is vibrating with a generic frequency. Run this app locally with Ollama to start a fully unscripted, dynamic chat with me!"
    ]
  };

  const pool = fallbacks[faction] || ["Understood. Signal logged."];
  return pool[Math.floor(Math.random() * pool.length)];
}
