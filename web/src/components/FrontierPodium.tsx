"use client";

import type { ModelSummary } from "@/lib/api";

// Gold / Silver / Bronze podium for Frontier models ranked by best value
// (lowest SIT score / cost-per-IQ). Lower SIT score = cheaper per unit of
// intelligence = better value. The homepage passes its live models array, so
// this podium updates automatically whenever prices / SIT scores move.
const PODIUM = [
  { medal: "Gold", color: "#E8C15A", rank: 1, height: 150 },
  { medal: "Silver", color: "#B8B8C0", rank: 2, height: 118 },
  { medal: "Bronze", color: "#CD8A54", rank: 3, height: 92 },
];

const GOLD = "#C4A038";
const CREAM = "#F5F3EB";
const MUTED = "#8A8A88";
const BG_CARD = "#1C1A18";

export default function FrontierPodium({ models }: { models: ModelSummary[] }) {
  // Frontier models with a valid SIT score, best value (lowest score) first.
  const frontier = models
    .filter((m) => (m.tier || "").toLowerCase() === "frontier")
    .filter((m) => typeof m.sit_score === "number" && isFinite(m.sit_score) && m.sit_score > 0)
    .sort((a, b) => a.sit_score - b.sit_score)
    .slice(0, 3);

  if (frontier.length === 0) return null;

  // Order visually: Silver (2nd) left, Gold (1st) centre, Bronze (3rd) right.
  const order = [frontier[1], frontier[0], frontier[2]].filter(Boolean);

  return (
    <section
      style={{
        maxWidth: "1320px",
        margin: "0 auto",
        padding: "22px 28px 0",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "10px",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "18px", fontWeight: 600, margin: 0, color: CREAM }}>
          Frontier Best Value — Podium
        </h2>
        <span style={{ fontSize: "12.5px", color: MUTED }}>
          Lowest cost per unit of intelligence (SIT score) · updates live as prices move
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", gap: "14px", minHeight: 210 }}>
        {order.map((m) => {
          const meta = PODIUM.find((p) => p.rank === frontier.indexOf(m) + 1)!;
          return (
            <div
              key={m.model_id}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: "10px",
              }}
            >
              <div
                style={{
                  textAlign: "center",
                  padding: "10px 14px 6px",
                  borderRadius: 10,
                  background: BG_CARD,
                  border: `1px solid ${meta.color}44`,
                  width: "100%",
                }}
              >
                <div style={{ color: meta.color, fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em" }}>
                  {meta.medal.toUpperCase()}
                </div>
                <div style={{ color: CREAM, fontSize: "15px", fontWeight: 600, margin: "4px 0 2px", lineHeight: 1.25 }}>
                  {m.name.split(":").pop()?.trim()}
                </div>
                <div style={{ fontSize: "12px", color: MUTED }}>{m.provider}</div>
                <div style={{ display: "flex", gap: "14px", justifyContent: "center", marginTop: "6px", fontSize: "12.5px" }}>
                  <span style={{ color: GOLD, fontWeight: 600 }}>SIT {m.sit_score}</span>
                  <span style={{ color: CREAM }}>${m.blended_price_per_m.toFixed(2)}/M</span>
                </div>
              </div>
              {/* Podium block */}
              <div
                style={{
                  width: "100%",
                  height: meta.height,
                  borderRadius: "6px 6px 0 0",
                  background: `linear-gradient(180deg, ${meta.color}cc, ${meta.color}55)`,
                  border: `1px solid ${meta.color}66`,
                }}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}