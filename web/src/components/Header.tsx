import Link from "next/link";

export function Header({ activePage = "" }: { activePage?: string }) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 30,
        background: "#0a0a0a",
        borderBottom: "1px solid #222",
      }}
    >
      <div
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "0 28px",
          height: "56px",
          display: "flex",
          alignItems: "center",
          gap: "28px",
        }}
      >
        <Link
          href="/"
          style={{
            fontSize: "15px",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: "#f2f2f2",
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          InferenceIndexer<span style={{ color: "#C4A038" }}>.ai</span>
        </Link>
        <div
          style={{
            flex: 1,
            maxWidth: "340px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            height: "30px",
            padding: "0 10px",
            border: "1px solid #262626",
            borderRadius: "4px",
            background: "#111112",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
              color: "#6a6a6a",
            }}
          >
            /
          </span>
          <span
            style={{
              flex: 1,
              color: "#6a6a6a",
              fontFamily: "Inter, sans-serif",
              fontSize: "12.5px",
            }}
          >
            Search 316 models...
          </span>
        </div>
        <div style={{ flex: 1 }} />
        <nav style={{ display: "flex", alignItems: "center", gap: "22px" }}>
          <Link
            href="/api-docs"
            style={{
              fontSize: "12.5px",
              color: activePage === "api" ? "#C4A038" : "#8a8a8a",
              textDecoration: "none",
            }}
          >
            API
          </Link>
          <Link
            href="/methodology"
            style={{
              fontSize: "12.5px",
              color: activePage === "methodology" ? "#C4A038" : "#8a8a8a",
              textDecoration: "none",
            }}
          >
            Methodology
          </Link>
          <Link
            href="/about"
            style={{
              fontSize: "12.5px",
              color: activePage === "about" ? "#C4A038" : "#8a8a8a",
              textDecoration: "none",
            }}
          >
            About
          </Link>
          <span style={{ width: "1px", height: "14px", background: "#222", display: "block" }} />
          <a
            href="#login"
            style={{ fontSize: "12.5px", color: "#8a8a8a", textDecoration: "none" }}
          >
            Login
          </a>
          <a
            href="#signup"
            style={{ fontSize: "12.5px", color: "#C4A038", textDecoration: "none" }}
          >
            Sign Up
          </a>
          <span style={{ width: "1px", height: "14px", background: "#222", display: "block" }} />
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#22c55e",
                display: "block",
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "11px",
                color: "#7a7a7a",
              }}
            >
              LIVE
            </span>
          </div>
        </nav>
      </div>
    </header>
  );
}

export function Footer({ models = 316, providers = 57, updatedAt = "" }: { models?: number; providers?: number; updatedAt?: string }) {
  const updated = updatedAt || new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC";
  return (
    <footer style={{ borderTop: "1px solid #1a1a1a", background: "#0a0a0a", marginTop: "auto" }}>
      <div
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "22px 28px 34px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        <div style={{ fontSize: "12px", color: "#8a8a8a" }}>
          InferenceIndexer.ai · Independent price index for AI inference
        </div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          <Link href="/methodology" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Methodology
          </Link>
          <Link href="/api-docs" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            API Docs
          </Link>
          <Link href="/about" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            About
          </Link>
          <a href="#privacy" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Privacy Policy
          </a>
        </div>
        <div
          style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "11.5px",
            color: "#5f5f5f",
          }}
        >
          {models} models · {providers} providers · Last updated: {updated}
        </div>
      </div>
    </footer>
  );
}
