// Tiny dependency-free SVG sparkline for an agent's wealth/happiness over days.
export default function Sparkline({ series, accessor, color, label, unit = "" }) {
  const pts = (series || []).map((d) => ({ x: d.day, y: accessor(d) }));
  if (pts.length < 2) return <div className="muted">Not enough history yet.</div>;

  const W = 280, H = 48, pad = 4;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (x) => pad + ((x - minX) / (maxX - minX || 1)) * (W - pad * 2);
  const sy = (y) => H - pad - ((y - minY) / (maxY - minY || 1)) * (H - pad * 2);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");
  const area = `${line} L${sx(maxX).toFixed(1)},${H - pad} L${sx(minX).toFixed(1)},${H - pad} Z`;
  const last = ys[ys.length - 1];

  return (
    <div className="spark">
      <div className="spark-head">
        <span>{label}</span>
        <span className="spark-val" style={{ color }}>{unit}{Math.round(last)}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="spark-svg">
        <path d={area} fill={color} opacity="0.12" />
        <path d={line} fill="none" stroke={color} strokeWidth="1.5" />
        <circle cx={sx(maxX)} cy={sy(last)} r="2.5" fill={color} />
      </svg>
    </div>
  );
}
