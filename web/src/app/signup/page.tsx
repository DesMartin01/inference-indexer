"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    setMessage("Check your email for a verification link.");
    setLoading(false);
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
          Create your account
        </h1>
        <p
          style={{
            fontSize: "13px",
            color: "#8a8a8a",
            marginBottom: "24px",
          }}
        >
          Get a free API key for the InferenceIndexer API. 10,000 requests/day.
        </p>

        {message && (
          <div
            style={{
              background: "#1a2a1a",
              border: "1px solid #2a4a2a",
              borderRadius: "6px",
              padding: "12px 16px",
              marginBottom: "16px",
              fontSize: "13px",
              color: "#7ec47e",
            }}
          >
            {message}
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

        <form onSubmit={handleSignup}>
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
            placeholder="Password (min 8 characters)"
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
            {loading ? "Creating..." : "Create account"}
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
          Already have an account?{" "}
          <a
            href="/login"
            style={{ color: "#C4A038", textDecoration: "none" }}
          >
            Log in
          </a>
        </p>
      </div>
    </div>
  );
}
