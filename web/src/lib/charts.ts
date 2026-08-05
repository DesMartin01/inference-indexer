// Shared chart path-generation utilities (pure functions, server-safe)

export interface SparkPath {
  line: string;
  area: string;
  min: number;
  max: number;
  pts: [number, number][];
  gridLines: { y: string; top: string; label: string }[];
}

export function buildSparkPath(
  vals: number[],
  opts: { x0?: number; x1?: number; top?: number; bot?: number; height?: number } = {},
): SparkPath {
  const X0 = opts.x0 ?? 8;
  const X1 = opts.x1 ?? 580;
  const TOP = opts.top ?? 12;
  const BOT = opts.bot ?? 128;
  const height = opts.height ?? 148;

  if (vals.length === 0) {
    return { line: "", area: "", min: 0, max: 0, pts: [], gridLines: [] };
  }
  if (vals.length === 1) {
    vals = [vals[0], vals[0]];
  }

  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = (hi - lo) * 0.12 || 0.1;
  const min = lo - pad;
  const max = hi + pad;
  const span = max - min;
  const yOf = (v: number) => TOP + (1 - (v - min) / span) * (BOT - TOP);

  const pts: [number, number][] = vals.map((v, i) => [
    X0 + (i * (X1 - X0)) / (vals.length - 1),
    yOf(v),
  ]);

  const line = pts
    .map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1))
    .join(" ");
  const area = line + " L" + X1 + " " + BOT + " L" + X0 + " " + BOT + " Z";

  const ticks = [hi + pad * 0.3, (lo + hi) / 2, lo - pad * 0.3];
  const gridLines = ticks.map((t) => {
    const y = yOf(t);
    return {
      y: y.toFixed(1),
      top: ((y / height) * 100).toFixed(2) + "%",
      label: "$" + t.toFixed(2),
    };
  });

  return { line, area, min: lo, max: hi, pts, gridLines };
}

export function buildRowSpark(blended: number, change7d: number): string {
  const n = 9;
  const end = blended;
  const start = end / (1 + change7d / 100);

  // deterministic pseudo-random based on blended value
  const h = Math.abs(Math.round(blended * 9973)) % 9973;
  const pts: number[] = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const jitter =
      ((((h + i * 53) % 13) - 6) / 100) *
      (end - start === 0 ? 0.02 : Math.abs(end - start));
    pts.push(start + (end - start) * t + (i === 0 || i === n - 1 ? 0 : jitter));
  }

  const lo = Math.min(...pts);
  const hi = Math.max(...pts);
  const span = hi - lo || 1;
  const W = 84;
  const H = 18;
  const pad = 2;

  return pts
    .map((v, i) => {
      const x = pad + (i * (W - pad * 2)) / (n - 1);
      const y = pad + (1 - (v - lo) / span) * (H - pad * 2);
      return (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    })
    .join(" ");
}

export function buildChartPath(
  vals: number[],
  opts: { x0?: number; x1?: number; top?: number; bot?: number; height?: number; nTicks?: number } = {},
): SparkPath {
  const X0 = opts.x0 ?? 64;
  const X1 = opts.x1 ?? 992;
  const TOP = opts.top ?? 20;
  const BOT = opts.bot ?? 370;
  const height = opts.height ?? 400;
  const nTicks = opts.nTicks ?? 5;

  if (vals.length === 0) {
    return { line: "", area: "", min: 0, max: 0, pts: [], gridLines: [] };
  }
  if (vals.length === 1) {
    vals = [vals[0], vals[0]];
  }

  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = (hi - lo) * 0.14 || 0.2;
  const min = lo - pad;
  const max = hi + pad;
  const span = max - min;
  const yOf = (v: number) => TOP + (1 - (v - min) / span) * (BOT - TOP);

  const pts: [number, number][] = vals.map((v, i) => [
    X0 + (i * (X1 - X0)) / (vals.length - 1),
    yOf(v),
  ]);

  const line = pts
    .map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1))
    .join(" ");
  const area = line + " L" + X1 + " " + BOT + " L" + X0 + " " + BOT + " Z";

  const ticks: number[] = [];
  for (let i = 0; i < nTicks; i++) {
    ticks.push(max - (span / (nTicks - 1)) * i);
  }
  const gridLines = ticks.map((t) => {
    const y = yOf(t);
    return {
      y: y.toFixed(1),
      top: ((y / height) * 100).toFixed(2) + "%",
      label: "$" + t.toFixed(2),
    };
  });

  return { line, area, min: lo, max: hi, pts, gridLines };
}
