import Link from "next/link";

export interface HarnessRow {
  name: string;
  url: string | null;
  page_url: string | null;
  description: string;
  stars: number;
  tier: string | null;
  tier_rank: number | null;
  autonomy: string | null;
  recovery: string | null;
  license: string | null;
  source_category: string;
  sandbox: string;
  buy: string;
}

export interface HarnessTableData {
  title: string;
  rows: HarnessRow[];
}

const fmtStars = new Intl.NumberFormat("en-US");

const th: React.CSSProperties = {
  textAlign: "left",
  fontSize: 11.5,
  fontWeight: 600,
  color: "#8a8a8a",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  padding: "10px 14px",
  borderBottom: "1px solid #2a2a2a",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  fontSize: 13.5,
  color: "#c9c9c9",
  padding: "12px 14px",
  borderBottom: "1px solid #1e1e1e",
  verticalAlign: "top",
};

const tdNum: React.CSSProperties = {
  ...td,
  fontVariantNumeric: "tabular-nums",
  fontFeatureSettings: '"tnum"',
  whiteSpace: "nowrap",
};

function licenseBadge(signal: string | null): string {
  if (signal === "open-source") return "open";
  if (signal && signal.startsWith("restricted")) return "restricted";
  return "unknown";
}

function licenseColor(signal: string | null): string {
  if (signal === "open-source") return "#c9c9c9";
  return "#8a8a8a";
}

export default function HarnessTable({
  data,
  extraColumn,
}: {
  data: HarnessTableData;
  extraColumn?: "sandbox" | "buy";
}) {
  const columns = extraColumn === "sandbox"
    ? ["Harness", "What it is", "Stars", "Tier", "Autonomy", "Recovery", "Sandboxing", "License"]
    : extraColumn === "buy"
      ? ["Harness", "What it is", "Stars", "Tier", "Autonomy", "Recovery", "Build vs buy", "License"]
      : ["Harness", "What it is", "Stars", "Tier", "Autonomy", "Recovery", "License"];

  return (
    <div
      style={{
        background: "#16161a",
        border: "1px solid #2a2a2a",
        borderRadius: 8,
        overflowX: "auto",
        marginBottom: 36,
      }}
    >
      <h2
        style={{
          fontSize: 17,
          fontWeight: 600,
          color: "#C4A038",
          padding: "16px 16px 12px",
          margin: 0,
        }}
      >
        {data.title}{" "}
        <span
          style={{
            color: "#8a8a8a",
            fontWeight: 400,
            fontSize: 13,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          ({data.rows.length})
        </span>
      </h2>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} style={th}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.name}>
              <td style={{ ...td, color: "#e5e5e5", fontWeight: 500, whiteSpace: "nowrap" }}>
                {r.page_url ? (
                  <a
                    href={r.page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#e5e5e5", textDecoration: "none" }}
                  >
                    {r.name}
                  </a>
                ) : r.url ? (
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#e5e5e5", textDecoration: "none" }}
                  >
                    {r.name}
                  </a>
                ) : (
                  r.name
                )}
              </td>
              <td style={{ ...td, color: "#8a8a8a", fontSize: 13, maxWidth: 340 }}>
                {r.description}
              </td>
              <td style={tdNum}>{fmtStars.format(r.stars)}</td>
              <td style={td}>{r.tier ?? "unknown"}</td>
              <td style={td}>{r.autonomy ?? "n/a"}</td>
              <td style={td}>{r.recovery ?? "n/a"}</td>
              {extraColumn === "sandbox" && <td style={td}>{r.sandbox}</td>}
              {extraColumn === "buy" && <td style={td}>{r.buy}</td>}
              <td style={{ ...td, color: licenseColor(r.license) }}>
                {licenseBadge(r.license)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
