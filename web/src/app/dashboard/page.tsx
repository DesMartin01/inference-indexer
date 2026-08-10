"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

interface ApiUserData {
  email: string;
  plan: string;
  request_count: number;
  rate_limit_per_day: number;
  api_key: string;
}

export default function DashboardPage() {
  const [data, setData] = useState<ApiUserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [regenConfirm, setRegenConfirm] = useState(false);
  const router = useRouter();

  const fetchData = useCallback(async () => {
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      router.push("/login?redirect=/dashboard");
      return;
    }

    // Fetch API user data from our API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://api.inferenceindexer.ai";

    // First, get the API key from the api_users table via Supabase
    const { data: apiUserData, error: rlsError } = await supabase
      .from("api_users")
      .select("api_key, plan, request_count, rate_limit_per_day, email")
      .eq("auth_user_id", user.id)
      .single();

    if (rlsError || !apiUserData) {
      // Fallback: try by email
      const { data: apiUserByEmail, error: emailError } = await supabase
        .from("api_users")
        .select("api_key, plan, request_count, rate_limit_per_day, email")
        .eq("email", user.email)
        .single();

      if (emailError || !apiUserByEmail) {
        setError("Could not find your API key. Please contact support.");
        setLoading(false);
        return;
      }
      setData(apiUserByEmail);
    } else {
      setData(apiUserData);
    }

    // Fetch usage from our API
    if (apiUserData?.api_key || (await supabase.from("api_users").select("api_key").eq("email", user.email).single()).data?.api_key) {
      const key = apiUserData?.api_key || (await supabase.from("api_users").select("api_key").eq("email", user.email).single()).data?.api_key;
      try {
        const res = await fetch(`${apiUrl}/v1/auth/me`, {
          headers: { Authorization: `Bearer ${key}` },
        });
        if (res.ok) {
          const usageData = await res.json();
          setData((prev) => prev ? { ...prev, request_count: usageData.request_count || prev.request_count } : prev);
        }
      } catch {
        // Usage fetch is best-effort
      }
    }

    setLoading(false);
  }, [router]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCopy = async () => {
    if (!data?.api_key) return;
    try {
      await navigator.clipboard.writeText(data.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleRegenerate = async () => {
    if (!data?.api_key) return;
    setRegenerating(true);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://api.inferenceindexer.ai";
    try {
      const res = await fetch(`${apiUrl}/v1/auth/regenerate-key`, {
        method: "POST",
        headers: { Authorization: `Bearer ${data.api_key}` },
      });
      if (res.ok) {
        const result = await res.json();
        setData((prev) => prev ? { ...prev, api_key: result.api_key } : prev);
        setShowKey(true);
        setRegenConfirm(false);
      } else {
        setError("Failed to regenerate key. Please try again.");
      }
    } catch {
      setError("Failed to regenerate key. Please try again.");
    }
    setRegenerating(false);
  };

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0a",
        }}
      >
        <p style={{ color: "#8a8a8a", fontSize: "14px" }}>Loading...</p>
      </div>
    );
  }

  const maskedKey = data?.api_key
    ? data.api_key.slice(0, 8) + "••••••••••••••••••••••••••••••"
    : "";

  const curlExample = `curl -H "Authorization: Bearer ${data?.api_key || "YOUR_API_KEY"}" \\
  ${process.env.NEXT_PUBLIC_API_URL || "https://api.inferenceindexer.ai"}/v1/sit/composite/latest`;

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", padding: "40px 20px" }}>
      <div style={{ maxWidth: "640px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: "32px" }}>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: 600,
              color: "#e5e5e5",
              marginBottom: "4px",
            }}
          >
            Dashboard
          </h1>
          <p style={{ fontSize: "13px", color: "#8a8a8a" }}>
            {data?.email}
          </p>
        </div>

        {error && (
          <div
            style={{
              background: "#2a1a1a",
              border: "1px solid #4a2a2a",
              borderRadius: "6px",
              padding: "12px 16px",
              marginBottom: "20px",
              fontSize: "13px",
              color: "#e57474",
            }}
          >
            {error}
          </div>
        )}

        {/* API Key Card */}
        <div
          style={{
            background: "#16161a",
            border: "1px solid #2a2a2a",
            borderRadius: "8px",
            padding: "24px",
            marginBottom: "20px",
          }}
        >
          <h2
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "#C4A038",
              marginBottom: "16px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            API Key
          </h2>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            <code
              style={{
                flex: 1,
                background: "#0a0a0a",
                border: "1px solid #333",
                borderRadius: "6px",
                padding: "10px 14px",
                fontSize: "13px",
                color: "#e5e5e5",
                fontFamily: "var(--font-jetbrains-mono), monospace",
                wordBreak: "break-all",
              }}
            >
              {showKey ? data?.api_key : maskedKey}
            </code>
            <button
              onClick={() => setShowKey(!showKey)}
              style={{
                background: "#222",
                color: "#8a8a8a",
                border: "1px solid #333",
                borderRadius: "6px",
                padding: "10px 14px",
                fontSize: "12px",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {showKey ? "Hide" : "Show"}
            </button>
            <button
              onClick={handleCopy}
              style={{
                background: copied ? "#1a2a1a" : "#222",
                color: copied ? "#7ec47e" : "#8a8a8a",
                border: `1px solid ${copied ? "#2a4a2a" : "#333"}`,
                borderRadius: "6px",
                padding: "10px 14px",
                fontSize: "12px",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>

          {regenConfirm ? (
            <div
              style={{
                background: "#2a2a1a",
                border: "1px solid #4a4a2a",
                borderRadius: "6px",
                padding: "12px 16px",
                marginBottom: "12px",
              }}
            >
              <p
                style={{
                  fontSize: "12.5px",
                  color: "#e5e5e5",
                  marginBottom: "10px",
                }}
              >
                This will invalidate your old key immediately. Any apps using
                the old key will stop working. Continue?
              </p>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  style={{
                    background: regenerating ? "#333" : "#C4A038",
                    color: regenerating ? "#666" : "#0a0a0a",
                    border: "none",
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: regenerating ? "not-allowed" : "pointer",
                  }}
                >
                  {regenerating ? "Regenerating..." : "Yes, regenerate"}
                </button>
                <button
                  onClick={() => setRegenConfirm(false)}
                  style={{
                    background: "#222",
                    color: "#8a8a8a",
                    border: "1px solid #333",
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setRegenConfirm(true)}
              style={{
                background: "transparent",
                color: "#666",
                border: "none",
                fontSize: "12px",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
              }}
            >
              Generate new key
            </button>
          )}
        </div>

        {/* Usage Card */}
        <div
          style={{
            background: "#16161a",
            border: "1px solid #2a2a2a",
            borderRadius: "8px",
            padding: "24px",
            marginBottom: "20px",
          }}
        >
          <h2
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "#C4A038",
              marginBottom: "16px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Usage
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <div>
              <p
                style={{
                  fontSize: "11px",
                  color: "#666",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "4px",
                }}
              >
                Plan
              </p>
              <p
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  color: "#e5e5e5",
                  textTransform: "capitalize",
                }}
              >
                {data?.plan || "free"}
              </p>
            </div>
            <div>
              <p
                style={{
                  fontSize: "11px",
                  color: "#666",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "4px",
                }}
              >
                Daily limit
              </p>
              <p
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  color: "#e5e5e5",
                }}
              >
                {(data?.rate_limit_per_day || 10000).toLocaleString()}
              </p>
            </div>
            <div>
              <p
                style={{
                  fontSize: "11px",
                  color: "#666",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "4px",
                }}
              >
                Requests today
              </p>
              <p
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  color: "#e5e5e5",
                }}
              >
                {(data?.request_count || 0).toLocaleString()}
              </p>
            </div>
            <div>
              <p
                style={{
                  fontSize: "11px",
                  color: "#666",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "4px",
                }}
              >
                Remaining
              </p>
              <p
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  color: "#7ec47e",
                }}
              >
                {((data?.rate_limit_per_day || 10000) - (data?.request_count || 0)).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Quick Start */}
        <div
          style={{
            background: "#16161a",
            border: "1px solid #2a2a2a",
            borderRadius: "8px",
            padding: "24px",
            marginBottom: "20px",
          }}
        >
          <h2
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "#C4A038",
              marginBottom: "16px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Quick Start
          </h2>
          <p
            style={{
              fontSize: "12.5px",
              color: "#8a8a8a",
              marginBottom: "12px",
            }}
          >
            Try your API key:
          </p>
          <pre
            style={{
              background: "#0a0a0a",
              border: "1px solid #333",
              borderRadius: "6px",
              padding: "14px",
              fontSize: "12px",
              color: "#e5e5e5",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              overflow: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {curlExample}
          </pre>
          <p style={{ fontSize: "12.5px", color: "#666", marginTop: "12px" }}>
            Full docs at{" "}
            <a
              href="/api-docs"
              style={{ color: "#C4A038", textDecoration: "none" }}
            >
              API Documentation
            </a>
          </p>
        </div>

        {/* Sign Out */}
        <button
          onClick={handleSignOut}
          style={{
            background: "transparent",
            color: "#666",
            border: "1px solid #333",
            borderRadius: "6px",
            padding: "10px 20px",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
