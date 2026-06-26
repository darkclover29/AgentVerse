const base = "";

export async function getWorld() {
  return (await fetch(`${base}/api/world`)).json();
}
export async function getAgents() {
  return (await fetch(`${base}/api/agents`)).json();
}
export async function getClock() {
  return (await fetch(`${base}/api/clock`)).json();
}
export async function getNews(day) {
  return (await fetch(`${base}/api/news?day=${day}`)).json();
}
export async function getNewspaper(day) {
  return (await fetch(`${base}/api/newspaper?day=${day}`)).json();
}
export async function getGraph() {
  return (await fetch(`${base}/api/graph`)).json();
}
export async function getPlan(id) {
  return (await fetch(`${base}/api/agents/${id}/plan`)).json();
}
export async function getMemories(id) {
  return (await fetch(`${base}/api/agents/${id}/memories`)).json();
}
export async function getRelationships(id) {
  return (await fetch(`${base}/api/agents/${id}/relationships`)).json();
}
export async function getStatus() {
  return (await fetch(`${base}/api/status`)).json();
}
export async function getBusinesses() {
  return (await fetch(`${base}/api/businesses`)).json();
}
export async function getHistory(id) {
  return (await fetch(`${base}/api/agents/${id}/history`)).json();
}
export async function getReplay(day) {
  return (await fetch(`${base}/api/replay?day=${day}`)).json();
}
export async function step(ticks = 1) {
  return (
    await fetch(`${base}/api/step`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticks }),
    })
  ).json();
}
export async function reset() {
  return (await fetch(`${base}/api/reset`, { method: "POST" })).json();
}
export async function getAgentChats(id) {
  return (await fetch(`${base}/api/agents/${id}/chats`)).json();
}
export async function getAgentTimeline(id) {
  return (await fetch(`${base}/api/agents/${id}/timeline`)).json();
}
export async function chatWithAgent(id, message, history) {
  return (
    await fetch(`${base}/api/agents/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    })
  ).json();
}
export async function updateTile(x, y, type) {
  return (
    await fetch(`${base}/api/world/tile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x, y, type }),
    })
  ).json();
}
export async function reproject() {
  return (await fetch(`${base}/api/reproject`, { method: "POST" })).json();
}
export function openSocket(onMessage) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const sock = new WebSocket(`${proto}://${location.host}/ws`);
  sock.onmessage = (e) => onMessage(JSON.parse(e.data));
  return sock;
}
