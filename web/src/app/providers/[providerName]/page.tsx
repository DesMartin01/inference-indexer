import { notFound } from "next/navigation";
import Link from "next/link";
import { getProviderDetail, providerFaviconUrl, providerInitials } from "@/lib/api";
import { Header, Footer } from "@/components/Header";
import ProviderModelTable from "@/components/ProviderModelTable";
import type { Metadata } from "next";

const ACCENT = "#C4A038";
const GREEN = "#22c55e";

const TIER_COLOR: Record<string, string> = {
  frontier: ACCENT,
  standard: "#5b8def",
  budget: GREEN,
  micro: "#7a7a7a",
};

const TYPE_LABEL: Record<string, string> = {
  "self-host": "Self-Hosted",
  "aggregator": "Aggregator",
  "hybrid": "Hybrid",
};

const TYPE_COLOR: Record<string, string> = {
  "self-host": "#5b8def",
  "aggregator": ACCENT,
  "hybrid": "#a855f7",
};

function formatPrice(n: number): string {
  if (n === 0) return "$0";
  if (n < 0.01) return "$" + n.toFixed(4);
  if (n < 1) return "$" + n.toFixed(3);
  return "$" + n.toFixed(2);
}

function capitalizeTier(t: string): string {
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export async function generateMetadata({ params }: { params: Promise<{ providerName: string }> }): Promise<Metadata> {
  const { providerName } = await params;
  const decoded = decodeURIComponent(providerName);

  let provider;
  try {
    provider = await getProviderDetail(decoded);
  } catch {
    return {
      title: "Provider Not Found - InferenceIndexer.ai",
      robots: { index: false, follow: true },
    };
  }

  return {
    title: `${provider.name} - ${provider.model_count} Models | InferenceIndexer.ai`,
    description: `Compare inference pricing across ${provider.model_count} models ${provider.provider_type === "aggregator" ? "hosted" : "offered"} by ${provider.name}.`,
    alternates: { canonical: `https://www.inferenceindexer.ai/providers/${encodeURIComponent(decoded)}` },
  };
}

export default async function ProviderPage({ params }: { params: Promise<{ providerName: string }> }) {
  const { providerName } = await params;
  const decoded = decodeURIComponent(providerName);

  let provider;
  try {
    provider = await getProviderDetail(decoded);
  } catch {
    notFound();
  }

  const tierOrder = ["frontier", "standard", "budget", "micro"];
  const tiers = tierOrder.filter((t) => provider.tiers?.[t]);

  const allPrices = provider.models.map((m) => m.blended_price_per_m).filter((p) => p > 0);
  const minPrice = allPrices.length ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length ? Math.max(...allPrices) : 0;
  const avgPrice = allPrices.length ? allPrices.reduce((a, b) => a + b, 0) / allPrices.length : 0;
  const reasoningCount = provider.models.filter((m) => m.is_reasoning).length;
  const withAA = provider.models.filter((m) => m.aa_index_score != null).length;

  const typeLabel = TYPE_LABEL[provider.provider_type] || provider.provider_type;
  const typeColor = TYPE_COLOR[provider.provider_type] || "#7a7a7a";

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5" }}>
      <Header activePage="providers" />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 60px" }}>
        {/* Breadcrumb */}
        <div style={{ marginBottom: 24 }}>
          <Link href="/providers" style={{ color: "#8a8a8a", textDecoration: "none", fontSize: 13 }}>
            ← All Providers
          </Link>
        </div>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
          <span
            style={{
              width: 48,
              height: 48,
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
              const fav = providerFaviconUrl(provider.name);
              return fav ? (
                <img src={fav} alt={provider.name} width={28} height={28} style={{ width: 28, height: 28, objectFit: "contain" }} />
              ) : (
                <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 16, color: "#8f8f96" }}>
                  {providerInitials(provider.name)}
                </span>
              );
            })()}
          </span>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f2f2f2", margin: 0, lineHeight: 1.2 }}>
              {provider.name}
            </h1>
            <div style={{ display: "flex", gap: 10, marginTop: 6, alignItems: "center" }}>
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 3, border: `1px solid ${typeColor}`, color: typeColor, textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 500 }}>
                {typeLabel}
              </span>
              <span style={{ fontSize: 14, color: "#8a8a8a" }}>{provider.model_count} models hosted</span>
              {provider.direct_model_count > 0 && provider.provider_type !== "self-host" && (
                <span style={{ fontSize: 13, color: "#6a6a6a" }}>({provider.direct_model_count} own)</span>
              )}
              {provider.is_zdr && (
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 3, border: `1px solid ${GREEN}`, color: GREEN, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  ZDR
                </span>
              )}
              {provider.is_eu_sovereign && (
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 3, border: `1px solid #5b8def`, color: "#5b8def", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  EU Infra
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Aggregator note */}
        {provider.provider_type === "aggregator" && provider.owners.length > 0 && (
          <div style={{ marginBottom: 24, fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
            <strong style={{ color: "#c9c9c9" }}>{provider.name}</strong> is an aggregator that hosts models from{" "}
            {provider.owners.length} providers: {provider.owners.slice(0, 8).join(", ")}
            {provider.owners.length > 8 && ` and ${provider.owners.length - 8} others`}.
            Prices shown are what {provider.name} charges, not what the model owner charges.
          </div>
        )}

        {/* Stats row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 28 }}>
          <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#5f5f5f", marginBottom: 6 }}>Avg Price</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>{formatPrice(avgPrice)}/M</div>
          </div>
          <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#5f5f5f", marginBottom: 6 }}>Range</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>{formatPrice(minPrice)}-{formatPrice(maxPrice)}</div>
          </div>
          <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#5f5f5f", marginBottom: 6 }}>Reasoning</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>{reasoningCount}</div>
          </div>
          <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
            <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#5f5f5f", marginBottom: 6 }}>With AA Score</div>
            <div style={{ fontSize: 20, fontWeight: 600, color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>{withAA}</div>
          </div>
          {(() => {
            const selfHosted = provider.models.filter((m) => m.hosting_type === "self-hosted").length;
            const proxied = provider.models.filter((m) => m.hosting_type === "proxied").length;
            if (selfHosted === 0 && proxied === 0) return null;
            return (
              <div style={{ background: "#0d0d0d", border: "1px solid #1a1a1a", borderRadius: 8, padding: "14px 18px" }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#5f5f5f", marginBottom: 6 }}>Hosting</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>
                  {selfHosted > 0 && <span style={{ color: "#5b8def" }}>{selfHosted} self-hosted</span>}
                  {selfHosted > 0 && proxied > 0 && <span style={{ color: "#5f5f5f", margin: "0 4px" }}> / </span>}
                  {proxied > 0 && <span style={{ color: ACCENT }}>{proxied} proxied</span>}
                </div>
              </div>
            );
          })()}
        </div>

        {/* Tier breakdown */}
        {tiers.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#8a8a8a", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14 }}>
              Tier Breakdown
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${tiers.length}, 1fr)`, gap: 10 }}>
              {tiers.map((t) => {
                const td = provider.tiers[t];
                const color = TIER_COLOR[t] || "#7a7a7a";
                return (
                  <div key={t} style={{ background: "#0d0d0d", border: `1px solid ${color}33`, borderRadius: 8, padding: "12px 16px" }}>
                    <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color, marginBottom: 6 }}>{capitalizeTier(t)}</div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "#e5e5e5", fontVariantNumeric: "tabular-nums" }}>{formatPrice(td.avg_price)}/M</div>
                    <div style={{ fontSize: 12, color: "#6a6a6a", marginTop: 3 }}>{td.count} models</div>
                    <div style={{ fontSize: 11, color: "#5f5f5f" }}>{formatPrice(td.min_price)} - {formatPrice(td.max_price)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ZDR/EU notes */}
        {(provider.zdr_notes || provider.eu_notes) && (
          <div style={{ marginBottom: 28, fontSize: 13, color: "#8a8a8a", lineHeight: 1.6 }}>
            {provider.zdr_notes && <p><strong style={{ color: GREEN }}>ZDR:</strong> {provider.zdr_notes}</p>}
            {provider.eu_notes && <p><strong style={{ color: "#5b8def" }}>EU Sovereign:</strong> {provider.eu_notes}</p>}
          </div>
        )}

        {/* Model table */}
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "#8a8a8a", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14 }}>
          Hosted Models (click column to sort)
        </h2>
        <ProviderModelTable models={provider.models} providerName={provider.name} />
      </main>
      <Footer models={316} providers={71} updatedAt="" />
    </div>
  );
}
