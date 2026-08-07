"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

export function Header({ activePage = "" }: { activePage?: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [q, setQ] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [userEmail, setUserEmail] = useState("");

  // Sync with URL query param when on homepage
  useEffect(() => {
    const urlQ = searchParams.get("q");
    if (urlQ !== null) setQ(urlQ);
  }, [searchParams]);

  // Check auth state
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setLoggedIn(!!session);
      setUserEmail(session?.user?.email || "");
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setLoggedIn(!!session);
      setUserEmail(session?.user?.email || "");
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleSearch = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && q.trim()) {
      router.push(`/?q=${encodeURIComponent(q.trim())}`);
      // If already on homepage, scroll to table
      const table = document.getElementById("model-table");
      if (table) table.scrollIntoView({ behavior: "smooth" });
    }
  };

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
            display: "flex",
            alignItems: "center",
            gap: "7px",
            fontSize: "15px",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: "#f2f2f2",
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/profile-icon.png" alt="InferenceIndexer" width={20} height={20} style={{ borderRadius: "3px" }} />
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
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={handleSearch}
            placeholder="Search 316 models..."
            style={{
              flex: 1,
              color: "#c9c9c9",
              fontFamily: "Inter, sans-serif",
              fontSize: "12.5px",
              background: "transparent",
              border: "none",
              outline: "none",
              width: "100%",
            }}
          />
        </div>
        <div style={{ flex: 1 }} />
        <nav style={{ display: "flex", alignItems: "center", gap: "22px" }}>
          <Link
            href="/providers"
            style={{
              fontSize: "12.5px",
              color: activePage === "providers" ? "#C4A038" : "#8a8a8a",
              textDecoration: "none",
            }}
          >
            Providers
          </Link>
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
          {loggedIn ? (
            <Link
              href="/dashboard"
              style={{ fontSize: "12.5px", color: "#C4A038", textDecoration: "none" }}
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                style={{ fontSize: "12.5px", color: "#8a8a8a", textDecoration: "none" }}
              >
                Login
              </Link>
              <Link
                href="/signup"
                style={{ fontSize: "12.5px", color: "#C4A038", textDecoration: "none" }}
              >
                Sign Up
              </Link>
            </>
          )}
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
        <div style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "12px", color: "#8a8a8a" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/profile-icon.png" alt="InferenceIndexer" width={16} height={16} style={{ borderRadius: "2px" }} />
          InferenceIndexer.ai · Independent price index for AI inference
        </div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          <Link href="/providers" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Providers
          </Link>
          <Link href="/methodology" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Methodology
          </Link>
          <Link href="/api-docs" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            API Docs
          </Link>
          <Link href="/about" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            About
          </Link>
          <Link href="/privacy" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Privacy Policy
          </Link>
          <Link href="/terms" style={{ fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}>
            Terms of Service
          </Link>
          <a
            href="https://x.com/inferenceindex"
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#7a7a7a", textDecoration: "none" }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.7 }}>
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            @inferenceindex
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
