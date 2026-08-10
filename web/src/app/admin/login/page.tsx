"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLoginPage() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/admin/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        router.push("/admin");
        router.refresh();
        return;
      }
      setError(data.error || "Login failed.");
      setLoading(false);
    } catch (err) {
      setError("Network error. Try again.");
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "60px auto" }}>
      <h1 style={{ fontSize: 26, color: "var(--text-heading)", marginBottom: 8 }}>
        Admin Access
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
        This area is private. Enter the admin password to continue.
      </p>
      <form onSubmit={handleSubmit}>
        <label
          style={{
            display: "block",
            fontSize: 13,
            color: "var(--text-secondary)",
            marginBottom: 6,
          }}
        >
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoFocus
          style={{
            width: "100%",
            padding: 12,
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            borderRadius: 8,
            color: "var(--text-heading)",
            fontSize: 15,
            marginBottom: 16,
          }}
        />
        {error && (
          <p style={{ color: "var(--red)", fontSize: 13, marginBottom: 16 }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: 12,
            background: "var(--accent)",
            color: "var(--bg)",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Checking..." : "Unlock Admin"}
        </button>
      </form>
    </div>
  );
}