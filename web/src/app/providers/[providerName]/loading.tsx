export default function ProviderLoading() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", paddingBottom: 40 }}>
      <div style={{ maxWidth: 1320, margin: "0 auto", padding: "28px 28px" }}>
        <div style={{ marginBottom: 24 }}>
          <span style={{ fontSize: 13, color: "#5f5f5f" }}>Loading provider...</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#16161a", border: "1px solid #333" }} />
          <div>
            <div style={{ height: 28, width: 200, background: "#1a1a1a", borderRadius: 4, marginBottom: 8 }} />
            <div style={{ height: 12, width: 150, background: "#1a1a1a", borderRadius: 4 }} />
          </div>
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: 20, marginBottom: 16 }}>
            <div style={{ height: 16, width: 120, background: "#1a1a1a", borderRadius: 4, marginBottom: 12 }} />
            <div style={{ display: "flex", gap: 16 }}>
              <div style={{ height: 40, flex: 1, background: "#1a1a1a", borderRadius: 4 }} />
              <div style={{ height: 40, flex: 1, background: "#1a1a1a", borderRadius: 4 }} />
              <div style={{ height: 40, flex: 1, background: "#1a1a1a", borderRadius: 4 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}