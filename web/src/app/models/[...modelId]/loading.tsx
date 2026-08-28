export default function ModelLoading() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", paddingBottom: 40 }}>
      <div style={{ maxWidth: 1320, margin: "0 auto", padding: "28px 28px" }}>
        <div style={{ marginBottom: 24 }}>
          <span style={{ fontSize: 13, color: "#5f5f5f" }}>Loading model...</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: "#16161a", border: "1px solid #333" }} />
          <div>
            <div style={{ height: 28, width: 300, background: "#1a1a1a", borderRadius: 4, marginBottom: 8 }} />
            <div style={{ height: 12, width: 200, background: "#1a1a1a", borderRadius: 4 }} />
          </div>
        </div>
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, marginBottom: 28 }}>
          <div style={{ height: 22, width: 150, background: "#1a1a1a", borderRadius: 4, marginBottom: 16 }} />
          <div style={{ display: "flex", gap: 32 }}>
            <div style={{ height: 50, width: 100, background: "#1a1a1a", borderRadius: 4 }} />
            <div style={{ height: 50, width: 100, background: "#1a1a1a", borderRadius: 4 }} />
            <div style={{ height: 50, width: 100, background: "#1a1a1a", borderRadius: 4 }} />
            <div style={{ height: 50, width: 100, background: "#1a1a1a", borderRadius: 4 }} />
          </div>
        </div>
      </div>
    </div>
  );
}