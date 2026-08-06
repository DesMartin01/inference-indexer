"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/dashboard";
  const urlError = searchParams.get("error");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    router.push(redirectUrl);
    router.refresh();
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a0a0a",
        padding: "20px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          background: "#16161a",
          border: "1px solid #2a2a2a",
          borderRadius: "8px",
          padding: "32px",
        }}
      >
        <h1
          style={{
            fontSize: "22px",
            fontWeight: 600,
            color: "#e5e5e5",
            marginBottom: "4px",
          }}
        >
          Log in
        </h1>
        <p style={{ fontSize: "13px", color: "#8a8a8a", marginBottom: "24px" }}>
          Access your API key and dashboard.
        </p>

        {urlError === "auth_callback_failed" && (
          <div
            style={{
              background: "#2a1a1a",
              border: "1px solid #4a2a2a",
              borderRadius: "6px",
              padding: "12px 16px",
              marginBottom: "16px",
              fontSize: "13px",
              color: "#e57474",
            }}
          >
            Authentication failed. The link may have expired. Please try again.
          </div>
        )}

        {error && (
          <div
            style={{
              background: "#2a1a1a",
              border: "1px solid #4a2a2a",
              borderRadius: "6px",
              padding: "12px 16px",
              marginBottom: "16px",
              fontSize: "13px",
              color: "#e57474",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              width: "100%",
              background: "#0a0a0a",
              border: "1px solid #333",
              borderRadius: "6px",
              padding: "12px 14px",
              fontSize: "14px",
              color: "#e5e5e5",
              marginBottom: "12px",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              width: "100%",
              background: "#0a0a0a",
              border: "1px solid #333",
              borderRadius: "6px",
              padding: "12px 14px",
              fontSize: "14px",
              color: "#e5e5e5",
              marginBottom: "16px",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              background: loading ? "#333" : "#C4A038",
              color: loading ? "#666" : "#0a0a0a",
              border: "none",
              borderRadius: "6px",
              padding: "12px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              boxSizing: "border-box",
            }}
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <p
          style={{
            fontSize: "12.5px",
            color: "#666",
            marginTop: "20px",
            textAlign: "center",
          }}
        >
          Don&apos;t have an account?{" "}
          <a
            href="/signup"
            style={{ color: "#C4A038", textDecoration: "none" }}
          >
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}
