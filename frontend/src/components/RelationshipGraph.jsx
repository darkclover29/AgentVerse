import { useEffect, useRef, useState } from "react";

const FACTION_COLOR = {
  corp: "#4a9eff",
  hacker: "#b07cf0",
  syndicate: "#f0716a",
  unaligned: "#7d8799",
};
const FRIEND = "69, 201, 138";   // --good
const RIVAL = "229, 103, 95";    // --bad

/**
 * Dependency-free force-directed graph on a crisp (DPR-scaled) canvas.
 * - repulsion + edge springs + center gravity
 * - friend/rival edges toggleable; hover isolates a node's neighborhood
 * - labels on hover and on the most-connected nodes
 * - click a node to inspect that agent (onSelect)
 */
export default function RelationshipGraph({ data, onSelect, showFriend = true, showRival = true, selectedId = null }) {
  const canvasRef = useRef(null);
  const stateRef = useRef({ nodes: [], edges: [], drag: null, hover: null, moved: false });
  const sizeRef = useRef({ w: 800, h: 600 });
  const toggles = useRef({ showFriend, showRival, selectedId });
  toggles.current = { showFriend, showRival, selectedId };
  const [, force] = useState(0);

  useEffect(() => {
    const { w, h } = sizeRef.current;
    const oldNodes = new Map((stateRef.current.nodes || []).map((n) => [n.id, n]));

    const nodes = data.nodes.map((n, i) => {
      const old = oldNodes.get(n.id);
      if (old) {
        return {
          ...n,
          x: old.x,
          y: old.y,
          vx: old.vx,
          vy: old.vy,
          deg: 0,
        };
      }
      return {
        ...n,
        x: w / 2 + Math.cos((i / data.nodes.length) * 6.283) * 220 + (Math.random() - 0.5) * 40,
        y: h / 2 + Math.sin((i / data.nodes.length) * 6.283) * 220 + (Math.random() - 0.5) * 40,
        vx: 0, vy: 0, deg: 0,
      };
    });

    const index = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const edges = data.edges
      .map((e) => ({ ...e, s: index[e.source], t: index[e.target] }))
      .filter((e) => e.s && e.t);
    edges.forEach((e) => { e.s.deg++; e.t.deg++; });
    stateRef.current.nodes = nodes;
    stateRef.current.edges = edges;
    stateRef.current.index = index;
    force((v) => v + 1);
  }, [data]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf;
    let dpr = window.devicePixelRatio || 1;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(360, rect.width), h = Math.max(360, rect.height);
      dpr = window.devicePixelRatio || 1;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sizeRef.current = { w, h };
    }
    resize();
    window.addEventListener("resize", resize);

    function tick() {
      const { nodes, edges, drag } = stateRef.current;
      const { w, h } = sizeRef.current;
      const cx = w / 2, cy = h / 2;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 0.01) {
            dx = (Math.random() - 0.5) * 2;
            dy = (Math.random() - 0.5) * 2;
            d2 = dx * dx + dy * dy;
          }
          const d = Math.sqrt(d2);
          const f = 2000 / (d2 + 400);
          a.vx += (dx / d) * f; a.vy += (dy / d) * f;
          b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
        }
      }
      for (const e of edges) {
        let dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
        const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const target = e.kind === "rivalry" ? 170 : 95;
        const f = (d - target) * 0.01;
        e.s.vx += (dx / d) * f; e.s.vy += (dy / d) * f;
        e.t.vx -= (dx / d) * f; e.t.vy -= (dy / d) * f;
      }
      for (const n of nodes) {
        n.vx += (cx - n.x) * 0.002; n.vy += (cy - n.y) * 0.002;
        n.vx *= 0.85; n.vy *= 0.85;
        if (drag !== n) { n.x += n.vx; n.y += n.vy; }
        n.x = Math.max(14, Math.min(w - 14, n.x));
        n.y = Math.max(14, Math.min(h - 14, n.y));
      }
      draw();
      raf = requestAnimationFrame(tick);
    }

    function draw() {
      const { nodes, edges, hover } = stateRef.current;
      const { showFriend, showRival, selectedId } = toggles.current;
      const { w, h } = sizeRef.current;
      ctx.clearRect(0, 0, w, h);
      const focus = hover || nodes.find((n) => n.id === selectedId) || null;

      for (const e of edges) {
        if (e.kind === "friendship" && !showFriend) continue;
        if (e.kind === "rivalry" && !showRival) continue;
        const active = !focus || e.s === focus || e.t === focus;
        const base = e.kind === "rivalry" ? RIVAL : FRIEND;
        ctx.strokeStyle = `rgba(${base},${(active ? 0.5 : 0.05) * Math.min(1, e.weight / 60 + 0.3)})`;
        ctx.lineWidth = active ? 1.3 : 0.5;
        ctx.beginPath(); ctx.moveTo(e.s.x, e.s.y); ctx.lineTo(e.t.x, e.t.y); ctx.stroke();
      }
      for (const n of nodes) {
        const active = !focus || n === focus || isNeighbor(n, focus, edges);
        const r = 3.5 + Math.min(9, n.deg * 0.55);
        ctx.globalAlpha = active ? 1 : 0.18;
        ctx.fillStyle = FACTION_COLOR[n.faction] || "#7d8799";
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 6.283); ctx.fill();
        if (n.id === selectedId) {
          ctx.globalAlpha = 1; ctx.strokeStyle = "#34d0bf"; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.arc(n.x, n.y, r + 4, 0, 6.283); ctx.stroke();
        }
        // label hovered node, selected node, and hubs
        if (n === focus || n.id === selectedId || (!focus && n.deg >= 8)) {
          ctx.globalAlpha = 1; ctx.fillStyle = "#e7eaf0";
          ctx.font = "600 11px Inter, sans-serif";
          ctx.fillText(n.name, n.x + r + 4, n.y + 3.5);
        }
      }
      ctx.globalAlpha = 1;
    }

    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);

  function nodeAt(mx, my) {
    const { nodes } = stateRef.current;
    let best = null, bd = 400;
    for (const n of nodes) {
      const d = (n.x - mx) ** 2 + (n.y - my) ** 2;
      if (d < bd) { bd = d; best = n; }
    }
    return best;
  }
  function pos(e) {
    const r = canvasRef.current.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  }

  return (
    <canvas
      ref={canvasRef}
      className="graph-canvas"
      style={{ width: "100%", height: "72vh", cursor: "grab", borderRadius: 12, display: "block" }}
      onMouseDown={(e) => { const [x, y] = pos(e); stateRef.current.drag = nodeAt(x, y); stateRef.current.moved = false; }}
      onMouseUp={(e) => {
        const node = stateRef.current.drag;
        if (node && !stateRef.current.moved && onSelect) onSelect(node.id);
        stateRef.current.drag = null;
      }}
      onMouseMove={(e) => {
        const [x, y] = pos(e);
        if (stateRef.current.drag) {
          stateRef.current.moved = true;
          stateRef.current.drag.x = x; stateRef.current.drag.y = y;
          stateRef.current.drag.vx = stateRef.current.drag.vy = 0;
        }
        stateRef.current.hover = nodeAt(x, y);
      }}
      onMouseLeave={() => { stateRef.current.drag = null; stateRef.current.hover = null; }}
    />
  );
}

function isNeighbor(n, focus, edges) {
  if (!focus) return true;
  for (const e of edges) {
    if ((e.s === focus && e.t === n) || (e.t === focus && e.s === n)) return true;
  }
  return false;
}
