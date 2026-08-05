// Sparkline React component (server-safe, no client interactivity)

export function Sparkline({ data, width = 640, height = 148, color = "#C4A038" }: { data: number[]; width?: number; height?: number; color?: string }) {
  if (data.length === 0) return null;

  const padded = data.length === 1 ? [data[0], data[0]] : data;
  const lo = Math.min(...padded);
  const hi = Math.max(...padded);
  const pad = (hi - lo) * 0.12 || 0.1;
  const min = lo - pad;
  const max = hi + pad;
  const span = max - min;

  const X0 = 8;
  const X1 = width - 8;
  const TOP = 12;
  const BOT = height - 20;

  const pts: [number, number][] = padded.map((v, i) => [
    X0 + (i * (X1 - X0)) / (padded.length - 1),
    TOP + (1 - (v - min) / span) * (BOT - TOP),
  ]);

  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = line + " L" + X1 + " " + BOT + " L" + X0 + " " + BOT + " Z";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Price history chart" style={{ display: "block", width: "100%", height: "auto" }}>
      <path d={area} fill={`${color}1a`} />
      <path d={line} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
