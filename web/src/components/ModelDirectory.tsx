// Server component: plain crawlable <a> index of every live model, grouped
// by creator namespace. Renders inside the served HTML (no "use client"),
// so crawlers that never execute JS still discover every model page.
// Human-facing ranked table (ModelTable) is untouched — this section renders
// below it as a quiet directory.
import Link from "next/link";
import type { ModelSummary } from "@/lib/api";
import { SITEMAP_EXCLUDED_MODEL_IDS } from "@/lib/sitemap-exclusions";

export default function ModelDirectory({ models }: { models: ModelSummary[] }) {
  const live = models.filter((m) => !SITEMAP_EXCLUDED_MODEL_IDS.has(m.model_id));
  const byCreator = new Map<string, ModelSummary[]>();
  for (const m of live) {
    const ns = m.model_id.split("/")[0] || "other";
    const bucket = byCreator.get(ns);
    if (bucket) bucket.push(m);
    else byCreator.set(ns, [m]);
  }
  const creators = [...byCreator.keys()].sort();

  return (
    <section
      id="model-directory"
      style={{
        maxWidth: "1320px",
        margin: "0 auto",
        padding: "36px 28px 44px",
        borderTop: "1px solid #1c1c1c",
        marginTop: 24,
      }}
    >
      <h2 style={{ fontSize: "18px", fontWeight: 600, color: "#f2f2f2", margin: 0 }}>
        All models by creator
      </h2>
      <p style={{ margin: "6px 0 20px", fontSize: "13px", color: "#8a8a8a" }}>
        {live.length} models across {creators.length} creators. Every model&apos;s
        pricing page, grouped alphabetically.
      </p>
      {creators.map((ns) => (
        <div key={ns} style={{ marginBottom: 22 }}>
          <h3 style={{ fontSize: "14px", color: "#C4A038", margin: "0 0 8px" }}>{ns}</h3>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, columns: "3 220px", columnGap: 28 }}>
            {(byCreator.get(ns) ?? []).map((m) => (
              <li key={m.model_id} style={{ breakInside: "avoid", padding: "2px 0" }}>
                <Link
                  href={`/models/${m.model_id}`}
                  style={{ fontSize: "13px", color: "#9a9a9a", textDecoration: "none" }}
                >
                  {m.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
