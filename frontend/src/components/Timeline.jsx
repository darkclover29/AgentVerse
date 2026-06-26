export default function Timeline({ day, maxDay, onScrub }) {
  return (
    <div className="timeline-wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
        <span className="section-title" style={{ margin: 0 }}>Time Machine</span>
        <span className="muted num">
          day {day} <span style={{ color: "var(--text-3)" }}>/ {maxDay}</span>
        </span>
      </div>
      <input type="range" min="0" max={Math.max(maxDay, 0)} value={day}
             onChange={(e) => onScrub(Number(e.target.value))} />
    </div>
  );
}
