import Link from "next/link";
import { getProviders, providerFaviconUrl, providerInitials, type ProviderSummary } from "@/lib/api";
import { Header, Footer } from "@/components/Header";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Inference Providers - Compare Pricing | InferenceIndexer.ai",
  description: "Compare inference pricing across 71 AI model providers. Model counts, price ranges, ZDR and EU sovereign status.",
  alternates: { canonical: "https://www.inferenceindexer.ai/providers" },
};

function formatPrice(n: number | null): string {
  if (n == null) return "N/A";
  if (n < 0.01) return "$" + n.toFixed(4);
  if (n < 1) return "$" + n.toFixed(3);
  return "$" + n.toFixed(2);
}

export default async function ProvidersPage() {
  let providers: ProviderSummary[] = [];
  try {
    const data = await getProviders();
    providers = data.providers;
  } catch {
    providers = [];
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5" }}>
      <Header activePage="" />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 60px" }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f2f2f2", marginBottom: 8 }}>
          Inference Providers
        </h1>
        <p style={{ fontSize: 15, color: "#8a8a8a", marginBottom: 32 }}>
          {providers.length} providers tracked across {providers.reduce((a, p) => a + p.model_count, 0)} models
        </p>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 700 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Provider</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Type</th>
                <th style={{ textAlign: "right", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Models</th>
                <th style={{ textAlign: "right", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Avg $/M</th>
                <th style={{ textAlign: "right", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Min $/M</th>
                <th style={{ textAlign: "right", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Max $/M</th>
                <th style={{ textAlign: "center", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>ZDR</th>
                <th style={{ textAlign: "center", padding: "10px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>EU</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.name} style={{ borderBottom: "1px solid #171717", transition: "background 90ms" }}>
                  <td style={{ padding: "12px" }}>
                    <Link
                      href={`/providers/${encodeURIComponent(p.name)}`}
                      style={{ display: "flex", alignItems: "center", gap: 10, color: "#f2f2f2", textDecoration: "none" }}
                    >
                      <span
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: "50%",
                          background: "#16161a",
                          border: "1px solid #33333a",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          overflow: "hidden",
                          flexShrink: 0,
                        }}
                      >
                        {(() => {
                          const fav = providerFaviconUrl(p.name);
                          return fav ? (
                            <img src={fav} alt={p.name} width={14} height={14} style={{ width: 14, height: 14, objectFit: "contain" }} />
                          ) : (
                            <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 9, color: "#8f8f96" }}>
                              {providerInitials(p.name)}
                            </span>
                          );
                        })()}
                      </span>
                      <span style={{ fontSize: 13.5, fontWeight: 500 }}>{p.name}</span>
                    </Link>
                  </td>
                  <td style={{ padding: "12px" }}>
                    <span style={{
                      fontSize: 10,
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                      padding: "2px 7px",
                      borderRadius: 3,
                      border: `1px solid ${p.provider_type === "aggregator" ? "#C4A038" : p.provider_type === "hybrid" ? "#a855f7" : "#5b8def"}`,
                      color: p.provider_type === "aggregator" ? "#C4A038" : p.provider_type === "hybrid" ? "#a855f7" : "#5b8def",
                    }}>
                      {p.provider_type === "self-host" ? "Self-Host" : p.provider_type === "hybrid" ? "Hybrid" : "Aggregator"}
                    </span>
                  </td>
                  <td style={{ padding: "12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>
                    {p.model_count > 0 ? p.model_count : `${p.endpoint_count} endpoints`}
                  </td>
                  <td style={{ padding: "12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.avg_price)}</td>
                  <td style={{ padding: "12px", textAlign: "right", color: "#6a6a6a", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.min_price)}</td>
                  <td style={{ padding: "12px", textAlign: "right", color: "#6a6a6a", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.max_price)}</td>
                  <td style={{ padding: "12px", textAlign: "center" }}>
                    {p.is_zdr ? <span style={{ color: "#22c55e", fontSize: 12 }}>Yes</span> : <span style={{ color: "#3a3a3a" }}>-</span>}
                  </td>
                  <td style={{ padding: "12px", textAlign: "center" }}>
                    {p.is_eu_sovereign ? <span style={{ color: "#5b8def", fontSize: 12 }}>Yes</span> : <span style={{ color: "#3a3a3a" }}>-</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
      <Footer models={316} providers={71} updatedAt="" />
    </div>
  );
}
