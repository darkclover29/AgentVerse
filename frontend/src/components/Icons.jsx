// Minimal inline SVG icon set (Lucide-style, stroke-based) — no emoji, themeable via currentColor.
const base = {
  width: 16, height: 16, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round",
};

export const Play = (p) => (
  <svg {...base} {...p}><polygon points="6 3 20 12 6 21 6 3" fill="currentColor" stroke="none" /></svg>
);
export const Pause = (p) => (
  <svg {...base} {...p}><rect x="6" y="4" width="4" height="16" fill="currentColor" stroke="none" />
    <rect x="14" y="4" width="4" height="16" fill="currentColor" stroke="none" /></svg>
);
export const StepForward = (p) => (
  <svg {...base} {...p}><line x1="6" y1="4" x2="6" y2="20" /><polygon points="9 5 19 12 9 19" fill="currentColor" stroke="none" /></svg>
);
export const FastForward = (p) => (
  <svg {...base} {...p}><polygon points="3 4 11 12 3 20" fill="currentColor" stroke="none" />
    <polygon points="12 4 20 12 12 20" fill="currentColor" stroke="none" /></svg>
);
export const Reset = (p) => (
  <svg {...base} {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></svg>
);
export const Refresh = (p) => (
  <svg {...base} {...p}><path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" /></svg>
);
export const Close = (p) => (
  <svg {...base} {...p}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
);
export const Target = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" fill="currentColor" /></svg>
);
export const Brain = (p) => (
  <svg {...base} {...p}><path d="M12 5a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 3 4 3 3 0 0 0 5 0 3 3 0 0 0 3-4 3 3 0 0 0-2-5 3 3 0 0 0-3-3z" /><path d="M12 5v14" /></svg>
);
export const City = (p) => (
  <svg {...base} {...p}><path d="M3 21h18" /><path d="M5 21V7l7-4 7 4v14" /><path d="M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01" /></svg>
);
export const Network = (p) => (
  <svg {...base} {...p}><circle cx="5" cy="6" r="2" /><circle cx="19" cy="6" r="2" /><circle cx="12" cy="18" r="2" /><path d="M6.7 7.2 10.6 16M17.3 7.2 13.4 16M7 6h10" /></svg>
);
export const Newspaper = (p) => (
  <svg {...base} {...p}>
    <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
    <path d="M18 14h-8M18 18h-8M16 6H10v4h6V6Z" />
  </svg>
);
