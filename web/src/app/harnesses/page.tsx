import type { Metadata } from "next";
import Link from "next/link";
import { Header, Footer } from "@/components/Header";
import HarnessTable from "@/components/HarnessTable";
import type { HarnessTableData } from "@/components/HarnessTable";
import harnessData from "@/../public/harnesses-data.json";

export const metadata: Metadata = {
  title: "AI Agent Harnesses Ranked by Category | InferenceIndexer.ai",
  description:
    "Agent harnesses ranked by category: personal agents, enterprise, small business. Stars and licenses are facts; category fit is our rubric. Pick the harness and the model as a pair.",
  alternates: { canonical: "https://www.inferenceindexer.ai/harnesses" },
  openGraph: {
    title: "AI Agent Harnesses Ranked by Category | InferenceIndexer.ai",
    description:
      "Agent harnesses ranked by category: personal agents, enterprise, small business. Pick the harness and the model as a pair.",
    url: "https://www.inferenceindexer.ai/harnesses",
    siteName: "InferenceIndexer.ai",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "AI Agent Harnesses Ranked by Category" }],
  },
};

interface SourceMeta {
  project_count: number | null;
  stars_captured: string | null;
  deep_dive_researched: number;
}

const data = harnessData as {
  generated_at: string;
  attribution: string;
  license: string;
  source_meta: SourceMeta;
  tables: {
    personal: HarnessTableData;
    enterprise: HarnessTableData;
    small_business: HarnessTableData;
    research?: HarnessTableData;
  };
};

const p: React.CSSProperties = {
  fontSize: 15,
  lineHeight: 1.65,
  color: "#c9c9c9",
  textWrap: "pretty",
};

const muted: React.CSSProperties = {
  fontSize: 13,
  color: "#8a8a8a",
  lineHeight: 1.6,
};

const rubricItem: React.CSSProperties = {
  ...muted,
  marginBottom: 8,
  paddingLeft: 16,
};

const jumpBtn: React.CSSProperties = {
  display: "inline-block",
  padding: "8px 18px",
  border: "1px solid #2a2a2a",
  borderRadius: 6,
  background: "#16161a",
  color: "#c9c9c9",
  fontSize: 13.5,
  textDecoration: "none",
};

export default function HarnessesPage() {
  const sm = data.source_meta;
  const researchedNote = `${sm.deep_dive_researched} of ${sm.project_count} harnesses researched in depth`;

  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="harnesses" />
      <main style={{ flex: 1, maxWidth: 1320, width: "100%", margin: "0 auto", padding: "40px 28px 60px" }}>
        <h1 style={{ fontSize: 30, fontWeight: 700, color: "#f2f2f2", marginBottom: 10, letterSpacing: "-0.01em" }}>
          Agent harnesses, ranked by category
        </h1>
        <p style={{ ...p, maxWidth: 780, marginBottom: 14 }}>
          Ranked from the best-of-Agent-Harnesses list ({sm.project_count} harnesses, rescored weekly). Stars
          and licenses are facts; fit-by-category is our rubric, not a verified benchmark. Pick the harness and
          the model as a pair.{" "}
          <Link href="/models" style={{ color: "#C4A038", textDecoration: "none" }}>
            We price the model side.
          </Link>
        </p>
        <p style={{ ...muted, marginBottom: 18 }}>
          Last refreshed {data.generated_at} · {researchedNote}
        </p>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 34 }}>
          <a href="#personal-agents" style={jumpBtn}>Personal agents</a>
          <a href="#enterprise-harnesses" style={jumpBtn}>Enterprise harnesses</a>
          <a href="#small-business-harnesses" style={jumpBtn}>Small business harnesses</a>
        </div>

        <HarnessTable data={data.tables.personal} anchorId="personal-agents" />
        <HarnessTable data={data.tables.enterprise} extraColumn="sandbox" anchorId="enterprise-harnesses" />
        <HarnessTable data={data.tables.small_business} extraColumn="buy" anchorId="small-business-harnesses" />

        <details
          style={{
            background: "#16161a",
            border: "1px solid #2a2a2a",
            borderRadius: 8,
            padding: "16px 20px",
            marginBottom: 28,
          }}
        >
          <summary style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", cursor: "pointer" }}>
            How the derived tables are filtered
          </summary>
          <div style={{ marginTop: 14 }}>
            <p style={{ ...muted, fontWeight: 600, color: "#c9c9c9", marginBottom: 6 }}>
              Enterprise harnesses
            </p>
            <p style={rubricItem}>
              Include if the license signal is open-source AND at least one of: strong sandboxing
              (container/VM/OS-level isolation) or durable recovery (execution state survives restarts).
            </p>
            <p style={{ ...muted, fontWeight: 600, color: "#c9c9c9", marginBottom: 6 }}>
              Small business harnesses
            </p>
            <p style={rubricItem}>
              Include if the harness is a runnable runtime (not a skill pack, curated list, benchmark suite, or
              observability tool) AND either managed (buy, not build) or simple to adopt (installable without a
              platform team), AND at least 100 GitHub stars.
            </p>
            <p style={{ ...muted, fontWeight: 600, color: "#c9c9c9", marginBottom: 6 }}>Personal agents</p>
            <p style={rubricItem}>
              Direct category: always-on, self-hosted agents run as a daemon and talked to from chat apps. No
              filter.
            </p>
            <p style={rubricItem}>
              A research-harness table is prepared but withheld: the source list is still thin. It releases when
              the category grows.
            </p>
            <p style={rubricItem}>
              Full rubric wording: <Link href="/methodology#harness-tables" style={{ color: "#C4A038", textDecoration: "none" }}>Methodology, Harness Tables</Link>.
            </p>
          </div>
        </details>

        <div style={{ borderTop: "1px solid #222", paddingTop: 18 }}>
          <p style={muted}>
            {data.attribution} · {data.license}. Fit-by-category is InferenceIndexer&apos;s rubric applied to that
            data; stars and licenses are the source&apos;s facts.
          </p>
          <p style={{ ...muted, marginTop: 10 }}>
            Continue:{" "}
            <Link href="/for-agents" style={{ color: "#C4A038", textDecoration: "none" }}>For agents</Link>
            {" · "}
            <Link href="/models" style={{ color: "#C4A038", textDecoration: "none" }}>Model rankings</Link>
            {" · "}
            <Link href="/api-docs" style={{ color: "#C4A038", textDecoration: "none" }}>API docs</Link>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
